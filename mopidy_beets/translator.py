import logging
import urllib.error
import urllib.parse
import urllib.request

from mopidy.models import Album, Artist, Track


logger = logging.getLogger(__name__)


def parse_date(data):
    # use 'original' dates if possible
    if "original_year" in data:
        day = data.get("original_day", None)
        month = data.get("original_month", None)
        year = data.get("original_year", None)
    elif "year" in data:
        day = data.get("day", None)
        month = data.get("month", None)
        year = data.get("year", None)
    else:
        return None
    # mopidy accepts dates as 'YYYY' or 'YYYY-MM-DD'
    if day is not None and month is not None:
        return "{year:04d}-{month:02d}-{day:02d}".format(
            day=day, month=month, year=year
        )
    else:
        return "{year:04d}".format(year=year)


def _apply_beets_mapping(target_class, mapping, data):
    """ evaluate a mapping of target keys and their source keys or callables

    'target_class' is the Mopidy model to be used for creating the item.
    'mapping' is a dict of {'target': source}.
    Here 'source' could be one of the following types:
        * string: the key for the corresponding value in 'data'
        * callable: a function with a dict ('data') as its only parameter
    """
    kwargs = {}
    for key, map_value in mapping.items():
        if map_value is None:
            value = None
        elif callable(map_value):
            value = map_value(data)
        else:
            value = data.get(map_value, None)
        # ignore None, empty strings or zeros (e.g. for length)
        if value:
            kwargs[key] = value
    return target_class(**kwargs) if kwargs else None


def _filter_none(values):
    return [value for value in values if value is not None]


def parse_artist(data, name_keyword):
    # see https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Artist
    mapping = {
        "uri": lambda d: assemble_uri(
            "beets:library:artist", id_value=d[name_keyword]
        ),
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


def parse_album(data, api):
    # see https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Album
    # The order of items is based on the above documentation.
    # Attributes without corresponding Beets data are mapped to 'None'.
    mapping = {
        "uri": lambda d: assemble_uri("beets:library:album", id_value=d["id"]),
        "name": "album",
        "artists": lambda d: _filter_none([parse_artist(d, "albumartist")]),
        "num_tracks": "tracktotal",
        "num_discs": "disctotal",
        "date": lambda d: parse_date(d),
        "musicbrainz_id": "mb_albumid",
        # TODO: 'images' is deprecated since v1.2 - move to Library.get_images
        "images": lambda d, api=api: _filter_none(
            [api.get_album_art_url(d["id"])]
        ),
    }
    return _apply_beets_mapping(Album, mapping, data)


def parse_track(data, api):
    # see https://docs.mopidy.com/en/latest/api/models/#mopidy.models.Track
    # The order of items is based on the above documentation.
    # Attributes without corresponding Beets data are mapped to 'None'.
    mapping = {
        "uri": lambda d: "beets:library:track;%s" % d["id"],
        "name": "title",
        "artists": lambda d: _filter_none([parse_artist(d, "artist")]),
        "album": lambda d, api=api: (
            api.get_album(d["album_id"]) if "album_id" in d else None
        ),
        "composers": lambda d: _filter_none([parse_artist(d, "composer")]),
        "performers": None,
        "genre": "genre",
        "track_no": "track",
        "disc_no": "disc",
        "date": lambda d: parse_date(d),
        "length": lambda d: int(d.get("length", 0) * 1000),
        "bitrate": lambda d: int(d.get("bitrate", 0) / 1000),
        "comment": "comments",
        "musicbrainz_id": "mb_trackid",
        "last_modified": lambda d: int(d.get("mtime", 0)),
    }
    return _apply_beets_mapping(Track, mapping, data)


def parse_uri(uri, uri_prefix=None):
    """ split a URI into an optional prefix and a value

        The format of a uri is similar to this:
            beets:library:album;Foo%20Bar
        (note the ampersand separating the value from the path)

        uri_prefix (optional):
            * remove the string from the beginning of uri
            * the match is valid only if the prefix is separated from the
              remainder of the URI with a color, an ampersand or it is equal
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
            # this prefix cannot be splitted
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


def assemble_uri(*args, **kwargs):
    base_path = ":".join(args)
    id_value = kwargs.pop("id_value", None)
    if id_value is None:
        return base_path
    else:
        # convert numbers and other non-strings
        if not isinstance(id_value, str):
            id_value = str(id_value)
        id_string = urllib.parse.quote(id_value)
        return "%s;%s" % (base_path, id_string)
