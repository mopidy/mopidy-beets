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
        self.api_endpoint = endpoint
        logger.info('Connecting to Beets remote library %s', endpoint)
        try:
            self.api.get(self.api_endpoint)
            self.has_connection = True
        except RequestException as e:
            logger.error('Beets error - connection failed: %s', e)
            self.has_connection = False

    @cache()
    def get_tracks(self):
        res = self._get('/item/').get('items')
        try:
            return self._parse_query(res)
        except Exception:
            return False

    @cache(ctl=16)
    def get_track(self, track_id, remote_url=False):
        return self._parse_track_data(self._get('/item/%s' % track_id),
                                      remote_url)

    @cache()
    def get_tracks_by(self, name):
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        res = self._get('/item/query/%s' %
                        urllib.quote(name)).get('results')
        return self._parse_reponse_tracks(res)

    @cache()
    def get_tracks_by_artist(self, artist):
        return [track for track in self.get_tracks_by(artist)
                if track["artist"] == artist]

    @cache()
    def get_tracks_by_title(self, title):
        return [track for track in self.get_tracks_by(title)
                if track["title"] == title]

    @cache()
    def get_artists(self):
        res = self._get('/artist/')
        try:
            return res[u'artist_names']
        except KeyError:
            return []

    @cache()
    def get_tracks_by_album_id(self, album_id):
        tracks = self._get('/item/')["items"]
        filtered_tracks = [track for track in tracks
                           if track["album_id"] == album_id]
        return self._parse_response_tracks(filtered_tracks)

    @cache()
    def _get_albums_by_attribute(self, attribute, value):
        return [album for album in self.get_albums_by(value)]

    @cache()
    def get_albums_by_artist(self, artist):
        return self._get_albums_by_attribute("albumartist", artist)

    @cache()
    def get_sorted_album_artists(self):
        albums = self._get('/album/')["albums"]
        # create a dictionary of artist -> artist_sorting
        # Meanwhile remove duplicates and filter empty artist fields.
        artists_sorter_dict = {album["albumartist"]: album["albumartist_sort"]
                               for album in albums if album["albumartist"]}
        # sort the keys according to their dict values
        return sorted(artists_sorter_dict.keys(),
                      key=lambda item: artists_sorter_dict[item])

    @cache()
    def get_albums_by(self, name):
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        albums = self._get('/album/query/%s' %
                           urllib.quote(name)).get('results')
        # deliver a list of album dictionaries
        # TODO: deliver Album objects
        return albums if albums else []

    def _get(self, url):
        url = self.api_endpoint + url
        logger.debug('Requesting %s' % url)
        try:
            req = self.api.get(url)
        except RequestException as e:
            logger.error('Request %s, failed with error %s', url, e)
            return None
        if req.status_code != 200:
            logger.error('Request %s, failed with status code %s',
                         url, req.status_code)
            return None
        else:
            return req.json()

    def _parse_response_tracks(self, response):
        tracks = []
        for dataset in (response or []):
            try:
                tracks.append(self._parse_track_data(dataset))
            except (ValueError, KeyError) as exc:
                logger.info("Failed to parse track data: %s", exc)
        return [self._parse_track_data(track) for track in response]

    def _parse_track_data(self, data, remote_url=False):
        if not data:
            return None

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
