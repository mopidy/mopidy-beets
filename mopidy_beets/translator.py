from mopidy.models import Album, Artist, Track


def parse_artist(data, is_album=False):
    kwargs = {}
    name_key = "albumartist" if is_album else "artist"
    mb_id_key = "mb_albumartistid" if is_album else "mb_artistid"
    if name_key in data:
        kwargs["name"] = data[name_key]
    if mb_id_key in data:
        kwargs["musicbrainz_id"] = data[mb_id_key]
    if kwargs:
        return Artist(**kwargs)
    else:
        return None


def parse_album(data, api_url):
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
        album_art_url = '%s/album/%s/art'.format(api_url, data['album_id'])
        album_kwargs['images'] = [album_art_url]
    album_kwargs['uri'] = 'beets:library:album;{0}'.format(data['id'])
    artist = parse_artist(data, is_album=True)
    if artist:
        album_kwargs['artists'] = [artist]
    return Album(**album_kwargs)


def parse_track(data, api_url, remote_url=False):
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
    artist = parse_artist(data)
    if artist:
        track_kwargs['artists'] = [artist]
    if remote_url:
        track_kwargs['uri'] = '%s/item/%s/file' % (api_url, data['id'])
    else:
        track_kwargs['uri'] = 'beets:track;%s' % data['id']
    track_kwargs['length'] = int(data.get('length', 0)) * 1000
    return Track(**track_kwargs)
