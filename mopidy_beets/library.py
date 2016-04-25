from __future__ import unicode_literals

import logging

from mopidy import backend, models
from mopidy.models import SearchResult

from .translator import assemble_uri, parse_uri


logger = logging.getLogger(__name__)


class BeetsLibraryProvider(backend.LibraryProvider):

    root_directory = models.Ref.directory(uri="beets:library",
                                          name='Beets library')

    def __init__(self, *args, **kwargs):
        super(BeetsLibraryProvider, self).__init__(*args, **kwargs)
        self.remote = self.backend.beets_api

    def _find_exact(self, query=None, uris=None):
        if not query:
            # Fetch all artists (browse library)
            return SearchResult(
                uri='beets:search',
                tracks=self.remote.get_artists())
        else:
            results = []
            if 'artist' in query:
                results.append(self.remote.get_tracks_by_artist(
                        query['artist'][0]))
            if 'album' in query:
                results.append(self.remote.get_tracks_by_title(
                        query['album'][0]))
            if len(results) > 1:
                # return only albums that match all restrictions
                results_set = set(results.pop(0))
                while results:
                    results_set.intersection_update(set(results.pop(0)))
                tracks = list(results_set)
            elif len(results) == 1:
                tracks = results[0]
            else:
                tracks = []
        return SearchResult(uri='beets:tracks', tracks=tracks)

    def browse(self, uri):
        if uri == self.root_directory.uri:
            directories = [("albums-by-artist", "Albums by Artist"),
                           ("albums-by-genre", "Albums by Genre"),
                           ("albums-by-year", "Albums by Year")]
            return [models.Ref.directory(name=label,
                        uri=assemble_uri(self.root_directory.uri, uri_suffix))
                    for uri_suffix, label in directories]
        parsed = parse_uri(uri, url_prefix=self.root_directory.uri)
        if not parsed:
            logger.error("Beets - failed to parse uri: %s", uri)
            return []
        elif parsed[0] == "albums-by-artist":
            if parsed[1] is None:
                # list all artists with albums
                keys = self.remote.get_sorted_unique_album_attributes(
                    "albumartist", True)
                return [models.Ref.directory(name=artist,
                            uri=assemble_uri(self.root_directory.uri,
                                             parsed[0], id_value=artist))
                        for artist in keys]
            else:
                artist_name = parsed[1]
                albums = self.remote.get_albums_by(
                    [("albumartist", artist_name)], True,
                    ["original_year+", "year+"])
                return [models.Ref.directory(uri=album.uri, name=album.name)
                        for album in albums]
        elif parsed[0] == "albums-by-genre":
            if parsed[1] is None:
                # list all genres with albums
                keys = self.remote.get_sorted_unique_album_attributes("genre",
                                                                      False)
                return [models.Ref.directory(name=genre,
                            uri=assemble_uri(self.root_directory.uri,
                                             parsed[0], id_value=genre))
                        for genre in keys]
            else:
                genre_name = parsed[1]
                albums = self.remote.get_albums_by([("genre", genre_name)],
                                                   True, ["album+"])
                return [models.Ref.directory(uri=album.uri, name=album.name)
                        for album in albums]
        elif parsed[0] == "albums-by-year":
            if parsed[1] is None:
                # list all genres with albums
                keys = self.remote.get_sorted_unique_album_attributes("year",
                                                                      False)
                return [models.Ref.directory(name=unicode(year),
                            uri=assemble_uri(self.root_directory.uri,
                                             parsed[0], id_value=year))
                        for year in keys]
            else:
                year = parsed[1]
                sort_keys = ["month+", "day+", "album+"]
                albums = self.remote.get_albums_by([("year", year)], True,
                                                   sort_keys)
                return [models.Ref.directory(uri=album.uri, name=album.name)
                        for album in albums]
        elif parsed[0] == "album":
            try:
                album_id = int(parsed[1])
            except ValueError:
                logger.error("Beets - invalid album ID: %s", parsed[1])
                return []
            tracks = self.remote.get_tracks_by([("album_id", album_id)], True,
                                               ["track+"])
            return [models.Ref.track(uri=track.uri, name=track.name)
                    for track in tracks]
        else:
            logger.error('Invalid browse URI: %s / %s', uri, current_path)
            return []

    def search(self, query=None, uris=None, exact=False):
        # TODO: add Album search
        logger.debug('Query "%s":' % query)
        if not self.remote.has_connection:
            return []

        if not query:
            # Fetch all data(browse library)
            return SearchResult(uri='beets:search',
                                tracks=self.remote.get_tracks())

        self._validate_query(query)
        search_list = []
        for (field, val) in query.iteritems():
            if field == "any":
                search_list.append(val[0])
            elif field == "album":
                search_list.append(("album", val[0]))
            elif field == "artist":
                search_list.append(("artist", val[0]))
            elif field == "track_name":
                search_list.append(("title", val[0]))
            elif field == "date":
                # TODO: there is no "date" in beets - just "day", "month"
                #       and "year". Determine the format of "date" and
                #       define a suitable date format string?
                search_list.append(("date", val[0]))
            else:
                logger.info("Ignoring unknown query key: %s", field)
        logger.debug('Search query "%s":' % search_list)
        tracks = self.remote.get_tracks_by(search_list, exact, [])
        uri = '-'.join([item if isinstance(item, str) else "=".join(item)
                        for item in search_list])
        return SearchResult(uri='beets:search-' + uri, tracks=tracks)

    def lookup(self, uri):
        # TODO: verify if we should do the same for Albums
        track_id = uri.split(";")[1]
        logger.debug('Beets track id for "%s": %s' % (track_id, uri))
        track = self.remote.get_track(track_id, True)
        return [track] if track else []

    def _validate_query(self, query):
        for values in query.values():
            if not values:
                raise LookupError('Missing query')
            for value in values:
                if not value:
                    raise LookupError('Missing query')
