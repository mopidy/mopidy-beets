from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, ClassVar, override

from mopidy import backend
from mopidy.models import Ref, SearchResult, Track
from mopidy.types import DistinctField, Query, SearchField, Uri

from mopidy_beets.browsers.albums import (
    AlbumsByArtistBrowser,
    AlbumsByGenreBrowser,
    AlbumsByYearBrowser,
)
from mopidy_beets.translator import assemble_uri, parse_uri

if TYPE_CHECKING:
    from mopidy_beets.actor import BeetsBackend
    from mopidy_beets.browsers import GenericBrowserBase
    from mopidy_beets.client import BeetsRemoteClient

logger = logging.getLogger(__name__)

# match dates of the following format:
#   YYYY, YYYY-MM, YYYY-MM-DD, YYYY/MM, YYYY/MM/DD
DATE_REGEX = re.compile(
    r"^(?P<year>\d{4})(?:[-/](?P<month>\d{1,2})(?:[-/](?P<day>\d{1,2}))?)?$"
)


class BeetsLibraryProvider(backend.LibraryProvider):
    root_directory = Ref.directory(
        uri=Uri("beets:library"),
        name="Beets library",
    )
    root_categorie_list: ClassVar[list[tuple[str, str, type[GenericBrowserBase]]]] = [
        ("albums-by-artist", "Albums by Artist", AlbumsByArtistBrowser),
        ("albums-by-genre", "Albums by Genre", AlbumsByGenreBrowser),
        ("albums-by-year", "Albums by Year", AlbumsByYearBrowser),
    ]

    backend: BeetsBackend
    remote: BeetsRemoteClient

    @override
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        assert self.root_directory  # noqa: S101
        self.remote = self.backend.beets_api
        self.category_browsers = []
        for key, label, browser_class in self.root_categorie_list:
            ref = Ref.directory(
                name=label,
                uri=assemble_uri(self.root_directory.uri, key),
            )
            browser = browser_class(ref, self.remote)
            self.category_browsers.append(browser)

    @override
    def browse(self, uri: Uri) -> list[Ref]:  # noqa: PLR0911
        logger.debug("Browsing Beets at: %s", uri)
        assert self.root_directory  # noqa: S101
        path, item_id = parse_uri(uri, uri_prefix=self.root_directory.uri)
        if path is None:
            logger.error("Beets - failed to parse uri: %s", uri)
            return []
        if uri == self.root_directory.uri:
            # top level - show the categories
            refs = [browser.ref for browser in self.category_browsers]
            refs.sort(key=lambda item: item.name)
            return refs
        if path == "album":
            # show an album
            if item_id is None:
                return []
            try:
                album_id = int(item_id)
            except ValueError:
                logger.error(f"Beets - invalid album ID in URI: {uri}")  # noqa: TRY400
                return []
            tracks = self.remote.get_tracks_by(
                [("album_id", album_id)],
                exact_text=True,
                sort_fields=["track+"],
            )
            return [Ref.track(uri=t.uri, name=t.name) for t in tracks]
        # show a generic category directory
        for browser in self.category_browsers:
            if (
                path
                == parse_uri(browser.ref.uri, uri_prefix=self.root_directory.uri)[0]
            ):
                if item_id is None:
                    return browser.get_toplevel()
                return browser.get_directory(item_id)
        logger.error("Beets - Invalid browse URI: %s / %s", uri, path)
        return []

    @override
    def search(  # noqa: C901, PLR0912
        self,
        query: Query[SearchField],
        uris: list[Uri] | None = None,
        exact: bool = False,
    ) -> SearchResult:
        # TODO: restrict the result to 'uris'
        logger.debug('Beets Query (exact=%s) within "%s": %s', exact, uris, query)
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
                    match = DATE_REGEX.search(str(val))
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
        tracks = self.remote.get_tracks_by(
            search_list,
            exact_text=exact,
            sort_fields=[],
        )
        uri = "-".join(
            [
                item if isinstance(item, str) else "=".join(map(str, item))
                for item in search_list
            ]
        )
        return SearchResult(
            uri=Uri(f"beets:search-{uri}"),
            tracks=tuple(tracks),
        )

    @override
    def lookup(self, uri: Uri) -> list[Track]:
        logger.debug("Beets lookup: %s", uri)
        assert self.root_directory  # noqa: S101
        path, item_id = parse_uri(uri, uri_prefix=self.root_directory.uri)
        if item_id is None:
            logger.info(f"Unknown item ID in Beets lookup URI: {uri}")
            return []
        if path == "track":
            tracks = [self.remote.get_track(item_id)]
        elif path == "album":
            tracks = self.remote.get_tracks_by(
                [("album_id", item_id)],
                exact_text=True,
                sort_fields=("disc+", "track+"),
            )
        elif path == "artist":
            artist_tracks = self.remote.get_tracks_by(
                [("artist", item_id)],
                exact_text=True,
                sort_fields=[],
            )
            composer_tracks = self.remote.get_tracks_by(
                [("composer", item_id)],
                exact_text=True,
                sort_fields=[],
            )
            # Append composer tracks to the artist tracks (unique items).
            tracks = list(set(artist_tracks + composer_tracks))
            tracks.sort(key=lambda t: (t.date or 0, t.disc_no or 0, t.track_no or 0))
        else:
            logger.info("Unknown Beets lookup URI: %s", uri)
            tracks = []
        # remove occourences of None
        return [t for t in tracks if t]

    @override
    def get_distinct(
        self,
        field: DistinctField,
        query: Query[SearchField] | None = None,
    ) -> set[str]:
        logger.debug("Beets distinct query: %s (uri=%s)", field, query)
        return self.remote.get_sorted_unique_track_attributes(field)

    def _validate_query(self, query: Query[SearchField]) -> None:
        for values in query.values():
            if not values:
                msg = "Missing query"
                raise LookupError(msg)
            for value in values:
                if not value:
                    msg = "Missing query"
                    raise LookupError(msg)
