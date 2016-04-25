from __future__ import unicode_literals

import logging
import time
import urllib

import requests
from requests.exceptions import RequestException

from .translator import parse_album, parse_track


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
        return parse_track(self._get('/item/%s' % track_id), self.api_endpoint,
                           remote_url)

    @cache(ctl=16)
    def get_album(self, album_id):
        return parse_album(self._get('/album/%s' % album_id),
                           self.api_endpoint)

    @cache()
    def get_tracks_by(self, attributes, exact_text, sort_fields):
        tracks = self._get_objects_by_attribute('/item/query/', attributes,
                                                exact_text, sort_fields)
        return self._parse_multiple_tracks(tracks)

    @cache()
    def get_albums_by(self, attributes, exact_text, sort_fields):
        albums = self._get_objects_by_attribute('/album/query/', attributes,
                                                exact_text, sort_fields)
        return self._parse_multiple_albums(albums)

    def _get_objects_by_attribute(self, base_path, attributes, exact_text,
                                  sort_fields):
        """ The beets web-api accepts queries like:
                /item/query/album_id:183/track:2
                /item/query/album:Foo
                /album/query/track_no:12/year+/month+
            Text-based matches (e.g. "album" or "artist") are case-independent
            "is in" matches. Thus we need to filter the result, since we want
            exact matches.

            @param attributes: attributes to be matched
            @type attribute: list of key/value pairs or strings
            @param exact_text: True for exact matches, False for
                               case-insensitive "is in" matches (only relevant
                               for text values - not integers)
            @type exact_text: bool
            @param sort_fields: fieldnames, each followed by "+" or "-"
            @type sort_fields: list of strings
            @rtype: list of json datasets describing tracks or albums
        """
        # assemble the query string
        query_parts = []
        # only used for "exact_text"
        exact_query_list = []

        def quote_and_encode(text):
            # utf-8 seems to be necessary for Python 2.7 and urllib.quote
            if isinstance(text, unicode):
                text = text.encode("utf-8")
            elif isinstance(text, (int, float)):
                text = str(text)
            # quoting for the query string
            return urllib.quote(text)

        for attribute in attributes:
            if isinstance(attribute, (str, unicode)):
                key = None
                value = quote_and_encode(attribute)
                query_parts.append(value)
            else:
                # the beets API accepts upper and lower case, but always
                # returns lower case attributes
                key = quote_and_encode(attribute[0].lower())
                value = quote_and_encode(attribute[1])
                query_parts.append("{0}:{1}".format(key, value))
            exact_query_list.append((key, value))
        # add sorting fields
        for sort_field in (sort_fields or []):
            if (len(sort_field) > 1) and (sort_field[-1] in ("-", "+")):
                query_parts.append(quote_and_encode(sort_field))
            else:
                logger.info("Beets - invalid sorting field ignore: %s",
                            sort_field)
        query_string = "/".join(query_parts)
        logger.debug("Beets query: %s", query_string)
        items = self._get(base_path + query_string)["results"]
        if exact_text:
            # verify that text attributes do not just test "is in", but match
            # equality
            for key, value in exact_query_list:
                if key is None:
                    # the value must match one of the
                    items = [item for item in items if value in item.values()]
                else:
                    # filtering is necessary only for text based attributes
                    if items and isinstance(items[0][key], str):
                        items = [item for item in items if item[key] == value]
        return items

    @cache()
    def get_artists(self):
        """ returns all artists of one or more tracks """
        names = self._get('/artist/')['artist_names']
        names.sort()
        # remove empty names
        return [name for name in names if name]

    @cache()
    def get_sorted_album_artists(self):
        """ returns all artists of tracks """
        sorted_albums = self._get('/album/query/albumartist_sort+')["results"]
        # remove all duplicates
        result = []
        previous_artist = None
        for album in sorted_albums:
            if previous_artist != album["albumartist"]:
                if album["albumartist"]:
                    result.append(album["albumartist"])
                previous_artist = album["albumartist"]
        return result

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

    def _parse_multiple_albums(self, album_datasets):
        albums = []
        for dataset in (album_datasets or []):
            try:
                albums.append(parse_album(dataset, self.api_endpoint))
            except (ValueError, KeyError) as exc:
                logger.info("Failed to parse album data: %s", exc)
        return [album for album in albums if album]

    def _parse_multiple_tracks(self, track_datasets):
        tracks = []
        for dataset in (track_datasets or []):
            try:
                tracks.append(parse_track(dataset, self.api_endpoint))
            except (ValueError, KeyError) as exc:
                logger.info("Failed to parse track data: %s", exc)
        return [track for track in tracks if track]
