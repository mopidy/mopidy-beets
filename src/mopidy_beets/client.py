from __future__ import annotations

import logging
import re
import time
import urllib.parse
import urllib.request
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import requests
from mopidy import httpclient
from mopidy.models import Album, Track
from mopidy.types import DistinctField, Uri
from requests.exceptions import RequestException

import mopidy_beets
from mopidy_beets.translator import parse_album, parse_track

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

logger = logging.getLogger(__name__)


class cache:  # noqa: N801
    def __init__(self, ctl: int = 8, ttl: int = 3600) -> None:
        self.cache: dict[tuple[Any, ...], tuple[Any, float]] = {}
        self.ctl = ctl
        self.ttl = ttl
        self._call_count = 1
        self.func: Callable[..., Any] | None = None

    def __call__[**P, R](self, func: Callable[P, R]) -> Callable[P, R]:
        def _memoized(*args: P.args, **kwargs: P.kwargs) -> R:
            self.func = func
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            try:
                value, last_update = self.cache[key]
                age = now - last_update
                if self._call_count >= self.ctl or age > self.ttl:
                    self._call_count = 1
                    raise AttributeError  # noqa: TRY301

                self._call_count += 1

            except (KeyError, AttributeError):
                value = func(*args, **kwargs)
                self.cache[key] = (value, now)
                return value

            except TypeError:
                return func(*args, **kwargs)

            else:
                return value

        return _memoized


class BeetsRemoteClient:
    def __init__(
        self,
        endpoint,
        proxy_config,
        request_timeout: int = 4,
    ) -> None:
        super().__init__()
        self._request_timeout = request_timeout
        self.api = self._get_session(proxy_config)
        self.api_endpoint = endpoint
        logger.info("Configured for Beets remote library %s", endpoint)

    def _get_session(self, proxy_config) -> requests.Session:
        session = requests.Session()
        session.headers["user-agent"] = httpclient.format_user_agent(
            f"{mopidy_beets.Extension.dist_name}/{mopidy_beets.Extension.version}"
        )
        if proxy := httpclient.format_proxy(proxy_config):
            session.proxies.update({"http": proxy, "https": proxy})  # pyright: ignore[reportCallIssue]
        return session

    @cache()
    def get_tracks(self) -> list[Track]:
        if (result := self._get("/item/")) is None:
            return []
        track_ids = result.get("item_ids") or []
        return [track for track_id in track_ids if (track := self.get_track(track_id))]

    @cache(ctl=16)
    def get_track(self, track_id: str | int) -> Track | None:
        if (result := self._get(f"/item/{track_id}")) is None:
            return None
        return parse_track(result, self)

    @cache(ctl=16)
    def get_album(self, album_id: str | int) -> Album | None:
        if (result := self._get(f"/album/{album_id}")) is None:
            return None
        return parse_album(result, self)

    @cache()
    def get_tracks_by(
        self,
        attributes: list[tuple[str, str | int]],
        *,
        exact_text: bool,
        sort_fields: Iterable[str],
    ) -> list[Track]:
        tracks = self._get_objects_by_attribute(
            "/item",
            attributes,
            exact_text=exact_text,
            sort_fields=sort_fields,
        )
        return self._parse_multiple_tracks(tracks)

    @cache()
    def get_albums_by(
        self,
        attributes: list[tuple[str, str | int]],
        *,
        exact_text: bool,
        sort_fields: Iterable[str],
    ) -> list[Album]:
        albums = self._get_objects_by_attribute(
            "/album",
            attributes,
            exact_text=exact_text,
            sort_fields=sort_fields,
        )
        return self._parse_multiple_albums(albums)

    def _get_objects_by_attribute(  # noqa: C901, PLR0912
        self,
        base_path: str,
        attributes: list[tuple[str, str | int]],
        *,
        exact_text: bool,
        sort_fields: Iterable[str],
    ) -> list[dict[str, Any]]:
        """The beets web-api accepts queries like:
            /item/query/album_id:183/track:2
            /item/query/album:Foo
            /album/query/track_no:12/year+/month+
        Text-based matches (e.g. 'album' or 'artist') are case-independent
        'is in' matches. Thus we need to filter the result, since we want
        exact matches.

        @param attributes: attributes to be matched
        @type attribute: list of key/value pairs or strings
        @param exact_text: True for exact matches, False for
                           case-insensitive 'is in' matches (only relevant
                           for text values - not integers)
        @param sort_fields: fieldnames, each followed by '+' or '-'
        @rtype: list of json datasets describing tracks or albums
        """
        # assemble the query string
        query_parts = []
        # only used for 'exact_text'
        exact_query_list = []

        def quote_and_encode(text):
            if isinstance(text, (int, float)):
                text = str(text)
            # Escape colons. The beets web API uses the colon to separate
            # field name and search term.
            text = text.replace(":", r"\:")
            # quoting for the query string
            return urllib.parse.quote(text)

        for attribute in attributes:
            if isinstance(attribute, str):
                query_parts.append(quote_and_encode(attribute))
                exact_query_list.append((None, attribute))
            else:
                # the beets API accepts upper and lower case, but always
                # returns lower case attributes
                key = attribute[0].lower()
                value = attribute[1]
                query_parts.append(f"{quote_and_encode(key)}:{quote_and_encode(value)}")
                # Try to add a simple regex filter, if we look for a string.
                # This will reduce the resource consumption of the query on
                # the server side (and for our 'exact' matching below).
                if exact_text and isinstance(value, str):
                    regex_query = f"^{re.escape(value)}$"
                    beets_query = (
                        f"{quote_and_encode(key)}::{quote_and_encode(regex_query)}"
                    )
                    logger.debug(f"Beets - regular expression query: {beets_query}")
                    query_parts.append(beets_query)
                else:
                    # in all other cases: use non-regex matching (if requested)
                    exact_query_list.append((key, value))
        # add sorting fields
        for sort_field in sort_fields or []:
            if (len(sort_field) > 1) and (sort_field[-1] in ("-", "+")):
                query_parts.append(quote_and_encode(sort_field))
            else:
                logger.info("Beets - invalid sorting field ignore: %s", sort_field)
        query_string = "/".join(query_parts)
        query_url = f"{base_path}/query/{query_string}"

        logger.debug("Beets query: %s", query_url)
        if (result := self._get(query_url)) is None:
            return []
        items = result["results"]
        if exact_text:
            # verify that text attributes do not just test 'is in', but match
            # equality
            for key, value in exact_query_list:
                if key is None:
                    # the value must match one of the item attributes
                    items = [item for item in items if value in item.values()]
                # filtering is necessary only for text based attributes
                elif items and isinstance(items[0][key], str):
                    items = [item for item in items if item[key] == value]
        return items

    @cache()
    def get_artists(self):
        """returns all artists of one or more tracks"""
        if (result := self._get("/artist/")) is None:
            return []
        return [name for name in sorted(result["artist_names"]) if name]

    def get_sorted_unique_track_attributes(self, field: DistinctField) -> set[str]:
        sort_field = {"albumartist": "albumartist_sort"}.get(field, field)
        return self._get_unique_attribute_values("/item", field, sort_field)

    def get_sorted_unique_album_attributes(self, field: str) -> set[str]:
        # Modern Beets exposes the multi-valued "genres" on albums (singular
        # "genre" was removed after the 2.x series); fall through to the
        # plural key so both /album/values/... and the legacy fallback work.
        field = {"genre": "genres"}.get(field, field)
        sort_field = {"albumartist": "albumartist_sort"}.get(field, field)
        return self._get_unique_attribute_values("/album", field, sort_field)

    @cache(ctl=32)
    def _get_unique_attribute_values(self, base_url, field, sort_field) -> set[str]:
        """Returns all artists, genres, ... of tracks or albums"""
        result = self._get(
            f"{base_url}/values/{field}?sort_key={sort_field}",
            raise_not_found=True,
        )
        return set(result["values"]) if result else set()

    def get_track_stream_url(self, track_id: str) -> Uri:
        return Uri(f"{self.api_endpoint}/item/{track_id}/file")

    @cache(ctl=32)
    def get_album_art_url(self, album_id: str) -> Uri | None:
        # Sadly we cannot determine, if the Beets library really contains album
        # art. Thus we need to ask for it and check the status code.
        url = f"{self.api_endpoint}/album/{album_id}/art"
        try:
            request = urllib.request.urlopen(url)  # noqa: S310
        except OSError:
            # DNS problem or similar
            return None
        request.close()
        return Uri(url) if request.getcode() == HTTPStatus.OK else None

    def _get(self, url, *, raise_not_found=False) -> dict[str, Any] | None:
        url = self.api_endpoint + url
        logger.debug(f"Beets - requesting {url}")
        try:
            req = self.api.get(url, timeout=self._request_timeout)
        except RequestException as e:
            logger.error(f"Beets - Request {url}, failed with error {e}")  # noqa: TRY400
            return None
        if req.status_code != HTTPStatus.OK:
            logger.error(
                "Beets - Request %s, failed with status code %s",
                url,
                req.status_code,
            )
            if (req.status_code == HTTPStatus.NOT_FOUND) and raise_not_found:
                # sometimes we need to distinguish empty and 'not found'
                msg = f"URL not found: {url}"
                raise KeyError(msg)
            return None
        return req.json()

    def _parse_multiple_albums(self, album_datasets) -> list[Album]:
        albums = list[Album]()
        for dataset in album_datasets or []:
            try:
                if album := parse_album(dataset, self):
                    albums.append(album)
            except (ValueError, KeyError) as exc:
                logger.info(f"Beets - Failed to parse album data: {exc}")
        return [album for album in albums if album]

    def _parse_multiple_tracks(self, track_datasets) -> list[Track]:
        tracks = list[Track]()
        for dataset in track_datasets or []:
            try:
                if track := parse_track(dataset, self):
                    tracks.append(track)
            except (ValueError, KeyError) as exc:
                logger.info(f"Beets - Failed to parse track data: {exc}")
        return [track for track in tracks if track]
