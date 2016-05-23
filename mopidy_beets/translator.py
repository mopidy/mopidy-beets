import logging
import urllib

from mopidy.models import Album, Artist, Track


logger = logging.getLogger(__name__)


def parse_artist(data, is_album=False):
    kwargs = {}
    name_key = 'albumartist' if is_album else 'artist'
    mb_id_key = 'mb_albumartistid' if is_album else 'mb_artistid'
    if name_key in data:
        kwargs['name'] = data[name_key]
    if mb_id_key in data:
        kwargs['musicbrainz_id'] = data[mb_id_key]
    if kwargs:
        return Artist(**kwargs)
    else:
        return None


def parse_album(data, api):
    if not data:
        return None
    album_kwargs = {}
    if 'tracktotal' in data:
        album_kwargs['num_tracks'] = int(data['tracktotal'])
    if 'album' in data:
        album_kwargs['name'] = data['album']
    if 'mb_albumid' in data:
        album_kwargs['musicbrainz_id'] = data['mb_albumid']
    if 'album_id' in data:
        album_art_url = api.get_album_art_url(data['album_id'])
        album_kwargs['images'] = [album_art_url]
    # TODO: retrieve the base URI from the current library
    album_kwargs['uri'] = assemble_uri('beets:library:album',
                                       id_value=data['id'])
    artist = parse_artist(data, is_album=True)
    if artist:
        album_kwargs['artists'] = [artist]
    return Album(**album_kwargs)


def parse_track(data, api):
    if not data:
        return None
    track_kwargs = {}
    if 'track' in data:
        track_kwargs['track_no'] = int(data['track'])
    if 'title' in data:
        track_kwargs['name'] = data['title']
    if 'date' in data:
        track_kwargs['date'] = data['date']
    if 'mb_trackid' in data:
        track_kwargs['musicbrainz_id'] = data['mb_trackid']
    if 'album_id' in data:
        track_kwargs['album'] = api.get_album(data['album_id'])
    artist = parse_artist(data)
    if artist:
        track_kwargs['artists'] = [artist]
    track_kwargs['uri'] = 'beets:track;%s' % data['id']
    track_kwargs['length'] = int(data.get('length', 0)) * 1000
    return Track(**track_kwargs)


def parse_uri(uri, uri_prefix=None, id_type=None):
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

        id_type (optional):
            * convert the parsed id value by calling the 'id_type' (e.g. 'int')

        The result of the function is a tuple of the uri and the id value.
        In case of an error the result is simply None.
    """
    if ';' in uri:
        result_uri, id_string = uri.split(';', 1)
    else:
        result_uri, id_string = uri, None
    if uri_prefix:
        if uri == uri_prefix:
            result_uri = ''
        elif result_uri.startswith(uri_prefix + ':'):
            result_uri = result_uri[len(uri_prefix) + 1:]
        else:
            # this prefix cannot be splitted
            logger.info('Failed to remove URI prefix (%s): %s',
                        uri_prefix, uri)
            return None
    if id_string:
        id_value = urllib.unquote(id_string.encode('ascii')).decode('utf-8')
        if id_type:
            try:
                id_value = id_type(id_value)
            except ValueError:
                logger.info('Failed to parse ID (%s) from uri: %s',
                            type(id_type), uri)
                return None
    else:
        id_value = None
    return result_uri, id_value


def assemble_uri(*args, **kwargs):
    base_path = ':'.join(args)
    id_value = kwargs.pop('id_value', None)
    if id_value is None:
        return base_path
    else:
        # convert numbers and other non-strings
        if not isinstance(id_value, (str, unicode)):
            id_value = str(id_value)
        id_string = urllib.quote(id_value.encode('utf-8'))
        return '%s;%s' % (base_path, id_string)
