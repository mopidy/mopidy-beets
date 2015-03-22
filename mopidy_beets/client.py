from __future__ import unicode_literals

import logging
import time
import urllib

from mopidy.models import Album, Artist, Track

import requests
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)


class cache(object):
    # TODO: merge this to util library

    def __init__(self, ctl=8, ttl=3600):
        self.cache = {}
        self.ctl = ctl
        self.ttl = ttl
        self._call_count = 1

    def __call__(self, func):
        def _memoized(*args):
            self.func = func
            now = time.time()
            try:
                value, last_update = self.cache[args]
                age = now - last_update
                if self._call_count >= self.ctl or \
                        age > self.ttl:
                    self._call_count = 1
                    raise AttributeError

                self._call_count += 1
                return value

            except (KeyError, AttributeError):
                value = self.func(*args)
                self.cache[args] = (value, now)
                return value

            except TypeError:
                return self.func(*args)
        return _memoized


class BeetsRemoteClient(object):

    def __init__(self, endpoint):
        super(BeetsRemoteClient, self).__init__()
        self.api = requests.Session()
        self.has_connection = False
        self.api_endpoint = endpoint
        logger.info('Connecting to Beets remote library %s', endpoint)
        try:
            self.api.get(self.api_endpoint)
            self.has_connection = True
        except RequestException as e:
            logger.error('Beets error: %s' % e)

    @cache()
    def get_tracks(self):
        track_ids = self._get('/item/').get('item_ids')
        tracks = []
        for track_id in track_ids:
            tracks.append(self.get_track(track_id))
        return tracks

    @cache(ctl=16)
    def get_track(self, id, remote_url=False):
        return self._convert_json_data(self._get('/item/%s' % id), remote_url)

    @cache()
    def get_item_by(self, name):
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        res = self._get('/item/query/%s' %
                        urllib.quote(name)).get('results')
        try:
            return self._parse_query(res)
        except Exception:
            return False

    @cache()
    def get_album_by(self, name):
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        res = self._get('/album/query/%s' %
                        urllib.quote(name)).get('results')
        try:
            return self._parse_query(res[0]['items'])
        except Exception:
            return False

    def _get(self, url):
        try:
            url = self.api_endpoint + url
            logger.debug('Requesting %s' % url)
            req = self.api.get(url)
            if req.status_code != 200:
                raise logger.error('Request %s, failed with status code %s' % (
                    url, req.status_code))

            return req.json()
        except Exception as e:
            return False
            logger.error('Request %s, failed with error %s' % (
                url, e))

    def _parse_query(self, res):
        if len(res) > 0:
            tracks = []
            for track in res:
                tracks.append(self._convert_json_data(track))
            return tracks
        return None

    def _convert_json_data(self, data, remote_url=False):
        if not data:
            return

        track_kwargs = {}
        album_kwargs = {}
        artist_kwargs = {}
        albumartist_kwargs = {}

        if 'track' in data:
            track_kwargs['track_no'] = int(data['track'])

        if 'tracktotal' in data:
            album_kwargs['num_tracks'] = int(data['tracktotal'])

        if 'artist' in data:
            artist_kwargs['name'] = data['artist']
            albumartist_kwargs['name'] = data['artist']

        if 'albumartist' in data:
            albumartist_kwargs['name'] = data['albumartist']

        if 'album' in data:
            album_kwargs['name'] = data['album']

        if 'title' in data:
            track_kwargs['name'] = data['title']

        if 'date' in data:
            track_kwargs['date'] = data['date']

        if 'mb_trackid' in data:
            track_kwargs['musicbrainz_id'] = data['mb_trackid']

        if 'mb_albumid' in data:
            album_kwargs['musicbrainz_id'] = data['mb_albumid']

        if 'mb_artistid' in data:
            artist_kwargs['musicbrainz_id'] = data['mb_artistid']

        if 'mb_albumartistid' in data:
            albumartist_kwargs['musicbrainz_id'] = (
                data['mb_albumartistid'])

        if 'album_id' in data:
            album_art_url = '%s/album/%s/art' % (
                self.api_endpoint, data['album_id'])
            album_kwargs['images'] = [album_art_url]

        if artist_kwargs:
            artist = Artist(**artist_kwargs)
            track_kwargs['artists'] = [artist]

        if albumartist_kwargs:
            albumartist = Artist(**albumartist_kwargs)
            album_kwargs['artists'] = [albumartist]

        if album_kwargs:
            album = Album(**album_kwargs)
            track_kwargs['album'] = album

        if remote_url:
            track_kwargs['uri'] = '%s/item/%s/file' % (
                self.api_endpoint, data['id'])
        else:
            track_kwargs['uri'] = 'beets:track;%s' % data['id']
        track_kwargs['length'] = int(data.get('length', 0)) * 1000

        track = Track(**track_kwargs)

        return track
