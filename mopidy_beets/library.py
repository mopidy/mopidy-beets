import logging
import re

from mopidy import backend, models
from mopidy.models import SearchResult

from mopidy_beets.browsers.albums import (
    AlbumsByArtistBrowser,
    AlbumsByGenreBrowser,
    AlbumsByYearBrowser,
)
from mopidy_beets.translator import assemble_uri, parse_uri


logger = logging.getLogger(__name__)

# match dates of the following format:
#   YYYY, YYYY-MM, YYYY-MM-DD, YYYY/MM, YYYY/MM/DD
DATE_REGEX = re.compile(
    r"^(?P<year>\d{4})(?:[-/](?P<month>\d{1,2})(?:[-/](?P<day>\d{1,2}))?)?$"
)


class BeetsLibraryProvider(backend.LibraryProvider):
    root_directory = models.Ref.directory(
        uri="beets:library", name="Beets library"
    )
    root_categorie_list = [
        ("albums-by-artist", "Albums by Artist", AlbumsByArtistBrowser),
        ("albums-by-genre", "Albums by Genre", AlbumsByGenreBrowser),
        ("albums-by-year", "Albums by Year", AlbumsByYearBrowser),
    ]

    def __init__(self, *args, **kwargs):
        super(BeetsLibraryProvider, self).__init__(*args, **kwargs)
        self.remote = self.backend.beets_api
        self.category_browsers = []
        for key, label, browser_class in self.root_categorie_list:
            ref = models.Ref.directory(
                name=label, uri=assemble_uri(self.root_directory.uri, key)
            )
            browser = browser_class(ref, self.remote)
            self.category_browsers.append(browser)

    def browse(self, uri):
        logger.debug("Browsing Beets at: %s", uri)
        path, item_id = parse_uri(uri, uri_prefix=self.root_directory.uri)
        if path is None:
            logger.error("Beets - failed to parse uri: %s", uri)
            return []
        elif uri == self.root_directory.uri:
            # top level - show the categories
            refs = [browser.ref for browser in self.category_browsers]
            refs.sort(key=lambda item: item.name)
            return refs
        elif path == "album":
            # show an album
            try:
                album_id = int(item_id)
            except ValueError:
                logger.error("Beets - invalid album ID in URI: %s", uri)
                return []
            tracks = self.remote.get_tracks_by(
                [("album_id", album_id)], True, ["track+"]
            )
            return [
                models.Ref.track(uri=track.uri, name=track.name)
                for track in tracks
            ]
        else:
            # show a generic category directory
            for browser in self.category_browsers:
                if (
                    path
                    == parse_uri(
                        browser.ref.uri, uri_prefix=self.root_directory.uri
                    )[0]
                ):
                    if item_id is None:
                        return browser.get_toplevel()
                    else:
                        return browser.get_directory(item_id)
            else:
                logger.error("Beets - Invalid browse URI: %s / %s", uri, path)
                return []

    def search(self, query=None, uris=None, exact=False):
        # TODO: restrict the result to 'uris'
        logger.debug(
            'Beets Query (exact=%s) within "%s": %s', exact, uris, query
        )
        if not self.remote.has_connection:
            return SearchResult(uri="beets:search-disconnected", tracks=[])

        self._validate_query(query)
        search_list = []
        for field, values in query.items():
            for val in values:
                # missing / unsupported fields: uri, performer
                if field == "any":
                    search_list.append(val)
                elif field == "album":
                    search_list.append(("album", val))
                elif field == "artist":
                    search_list.append(("artist", val))
                elif field == "albumartist":
                    search_list.append(("albumartist", val))
                elif field == "track_name":
                    search_list.append(("title", val))
                elif field == "track_no":
                    search_list.append(("track", val))
                elif field == "composer":
                    search_list.append(("composer", val))
                elif field == "genre":
                    search_list.append(("genre", val))
                elif field == "comment":
                    search_list.append(("comments", val))
                elif field == "date":
                    # supported date formats: YYYY, YYYY-MM, YYYY-MM-DD
                    # Days and months may consist of one or two digits.
                    # A slash (instead of a dash) is acceptable as a separator.
                    match = DATE_REGEX.search(val)
                    if match:
                        # remove None values
                        for key, value in match.groupdict().items():
                            if value:
                                search_list.append((key, int(value)))
                    else:
                        logger.info(
                            "Beets search: ignoring unknown date format (%s). "
                            'It should be "YYYY", "YYYY-MM" or "YYYY-MM-DD".',
                            val,
                        )
                else:
                    logger.info("Beets: ignoring unknown query key: %s", field)
                    break
        logger.debug("Beets search query: %s", search_list)
        tracks = self.remote.get_tracks_by(search_list, exact, [])
        uri = "-".join(
            [
                item if isinstance(item, str) else "=".join(item)
                for item in search_list
            ]
        )
        return SearchResult(uri="beets:search-" + uri, tracks=tracks)

    def lookup(self, uri=None, uris=None):
        logger.debug("Beets lookup: %s", uri or uris)
        if uri:
            # the older method (mopidy < 1.0): return a list of tracks
            # handle one or more tracks given with multiple semicolons
            logger.debug("Beets lookup: %s", uri)
            path, item_id = parse_uri(uri, uri_prefix=self.root_directory.uri)
            if path == "track":
                tracks = [self.remote.get_track(item_id)]
            elif path == "album":
                tracks = self.remote.get_tracks_by(
                    [("album_id", item_id)], True, ("disc+", "track+")
                )
            elif path == "artist":
                artist_tracks = self.remote.get_tracks_by(
                    [("artist", item_id)], True, []
                )
                composer_tracks = self.remote.get_tracks_by(
                    [("composer", item_id)], True, []
                )
                # Append composer tracks to the artist tracks (unique items).
                tracks = list(set(artist_tracks + composer_tracks))
                tracks.sort(key=lambda t: (t.date, t.disc_no, t.track_no))
            else:
                logger.info("Unknown Beets lookup URI: %s", uri)
                tracks = []
            # remove occourences of None
            return [track for track in tracks if track]
        else:
            # the newer method (mopidy>=1.0): return a dict of uris and tracks
            return {uri: self.lookup(uri=uri) for uri in uris}

    def get_distinct(self, field, query=None):
        logger.debug("Beets distinct query: %s (uri=%s)", field, query)
        if not self.remote.has_connection:
            return []
        else:
            return self.remote.get_sorted_unique_track_attributes(field)

    def _validate_query(self, query):
        for values in query.values():
            if not values:
                raise LookupError("Missing query")
            for value in values:
                if not value:
                    raise LookupError("Missing query")
