from __future__ import annotations

import logging
import urllib.parse
from typing import TYPE_CHECKING, Any

from mopidy.models import Album, Artist, Track
from mopidy.types import Uri

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mopidy_beets.client import BeetsRemoteClient

logger = logging.getLogger(__name__)


def parse_date(data: dict[str, Any]) -> str | None:
    # use 'original' dates if possible
    if "original_year" in data:
        day = data.get("original_day")
        month = data.get("original_month")
        year = data.get("original_year")
    elif "year" in data:
        day = data.get("day")
        month = data.get("month")
        year = data.get("year")
    else:
        return None
    # mopidy accepts dates as 'YYYY' or 'YYYY-MM-DD'
    if day is not None and month is not None:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return f"{year:04d}"


def _apply_beets_mapping[T](
    target_class: type[T],
    mapping: dict[str, str],
    data: dict[str, Any],
) -> T | None:
    """evaluate a mapping of target keys and their source keys or callables

    'target_class' is the Mopidy model to be used for creating the item.
    'mapping' is a dict of {'target': source}.
    Here 'source' could be one of the following types:
        * string: the key for the corresponding value in 'data'
        * callable: a function with a dict ('data') as its only parameter
    """
    kwargs: dict[str, Any] = {}
    for key, map_value in mapping.items():
        if map_value is None:
            value = None
        elif callable(map_value):
            value = map_value(data)
        else:
            value = data.get(map_value)
        # ignore None, empty strings or zeros (e.g. for length)
        if value:
            kwargs[key] = value
    return target_class(**kwargs) if kwargs else None


def _filter_none[T](values: Iterable[T | None]) -> list[T]:
    return [value for value in values if value is not None]


def parse_artist(data: dict[str, Any], name_keyword: str) -> Artist | None:
    # see https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Artist
    mapping = {
        "uri": lambda d: assemble_uri("beets:library:artist", id_value=d[name_keyword]),
        "name": name_keyword,
    }
    if name_keyword == "artist":
        mapping["sortname"] = "artist_sort"
        mapping["musicbrainz_id"] = "mb_artistid"
    elif name_keyword == "albumartist":
        mapping["sortname"] = "albumartist_sort"
        mapping["musicbrainz_id"] = "mb_albumartistid"
    else:
        # others - e.g. composers
        pass
    return _apply_beets_mapping(Artist, mapping, data)


def parse_album(data: dict[str, Any], _api: BeetsRemoteClient) -> Album | None:
    # see https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Album
    # The order of items is based on the above documentation.
    # Attributes without corresponding Beets data are mapped to 'None'.
    mapping = {
        "uri": lambda d: assemble_uri("beets:library:album", id_value=d["id"]),
        "name": "album",
        "artists": lambda d: _filter_none([parse_artist(d, "albumartist")]),
        "num_tracks": "tracktotal",
        "num_discs": "disctotal",
        "date": parse_date,
        "musicbrainz_id": "mb_albumid",
    }
    return _apply_beets_mapping(Album, mapping, data)


def parse_track(data: dict[str, Any], api: BeetsRemoteClient) -> Track | None:
    # see https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Track
    # The order of items is based on the above documentation.
    # Attributes without corresponding Beets data are mapped to 'None'.
    mapping = {
        "uri": lambda d: f"beets:library:track;{d['id']}",
        "name": "title",
        "artists": lambda d: _filter_none([parse_artist(d, "artist")]),
        "album": lambda d, api=api: (
            api.get_album(d["album_id"]) if d.get("album_id") else None
        ),
        "composers": lambda d: _filter_none([parse_artist(d, "composer")]),
        "performers": None,
        "genre": "genre",
        "track_no": "track",
        "disc_no": "disc",
        "date": parse_date,
        "length": lambda d: int(d.get("length", 0) * 1000),
        "bitrate": lambda d: int(d.get("bitrate", 0) / 1000),
        "comment": "comments",
        "musicbrainz_id": "mb_trackid",
        "last_modified": lambda d: int(d.get("mtime", 0)),
    }
    return _apply_beets_mapping(Track, mapping, data)


def parse_uri(
    uri: Uri,
    uri_prefix: str | None = None,
) -> tuple[str | None, str | int | None]:
    """Split a URI into an optional prefix and a value.

    The format of a uri is similar to this:
        beets:library:album;Foo%20Bar
    (note the ampersand separating the value from the path)

    uri_prefix (optional):
        * remove the string from the beginning of uri
        * the match is valid only if the prefix is separated from the
          remainder of the URI with a colon, an ampersand or it is equal
          to the full URI
        * the function returns 'None' if the uri_prefix cannot be removed
          (you should consider this an error condition)

    The result of the function is a tuple of the uri and the id value.
    In case of an error the result is simply None.
    """
    if ";" in uri:
        result_uri, id_string = uri.split(";", 1)
    else:
        result_uri, id_string = uri, None
    last_path_token = result_uri.split(":")[-1]
    if uri_prefix:
        if uri == uri_prefix:
            result_uri = ""
        elif result_uri.startswith(uri_prefix + ":"):
            result_uri = result_uri[len(uri_prefix) + 1 :]
        else:
            # this prefix cannot be split
            logger.info("Failed to remove URI prefix (%s): %s", uri_prefix, uri)
            return None, None
    if id_string is not None:
        id_value = urllib.parse.unquote(id_string)
        # convert track and album IDs to int
        if last_path_token in ("track", "album"):
            try:
                id_value = int(id_value)
            except ValueError:
                logger.info("Failed to parse integer ID from uri: %s", uri)
                return None, None
    else:
        id_value = None
    return result_uri, id_value


def assemble_uri(*args: str, id_value: str | None = None) -> Uri:
    base_path = ":".join(args)
    if id_value is None:
        return Uri(base_path)
    # convert numbers and other non-strings
    if not isinstance(id_value, str):
        id_value = str(id_value)
    id_string = urllib.parse.quote(id_value)
    return Uri(f"{base_path};{id_string}")
