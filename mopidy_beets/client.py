from __future__ import unicode_literals

import logging
import time
import urllib

from mopidy import httpclient

import requests
from requests.exceptions import RequestException

import mopidy_beets
from mopidy_beets.translator import parse_album, parse_track


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

    def __init__(self, endpoint, proxy_config):
        super(BeetsRemoteClient, self).__init__()
        self.api = self._get_session(proxy_config)
        self.api_endpoint = endpoint
        logger.info('Connecting to Beets remote library %s', endpoint)
        try:
            self.api.get(self.api_endpoint)
            self.has_connection = True
        except RequestException as e:
            logger.error('Beets error - connection failed: %s', e)
            self.has_connection = False

    def _get_session(self, proxy_config):
        proxy = httpclient.format_proxy(proxy_config)
        full_user_agent = httpclient.format_user_agent('/'.join((
            mopidy_beets.BeetsExtension.dist_name, mopidy_beets.__version__)))
        session = requests.Session()
        session.proxies.update({'http': proxy, 'https': proxy})
        session.headers.update({'user-agent': full_user_agent})
        return session

    @cache()
    def get_tracks(self):
        track_ids = self._get('/item/').get('item_ids') or []
        tracks = [self.get_track(track_id) for track_id in track_ids]
        return tracks

    @cache(ctl=16)
    def get_track(self, track_id):
        return parse_track(self._get('/item/%s' % track_id), self)

    @cache(ctl=16)
    def get_album(self, album_id):
        return parse_album(self._get('/album/%s' % album_id), self)

    @cache()
    def get_tracks_by(self, attributes, exact_text, sort_fields):
        tracks = self._get_objects_by_attribute('/item', attributes,
                                                exact_text, sort_fields)
        return self._parse_multiple_tracks(tracks)

    @cache()
    def get_albums_by(self, attributes, exact_text, sort_fields):
        albums = self._get_objects_by_attribute('/album', attributes,
                                                exact_text, sort_fields)
        return self._parse_multiple_albums(albums)

    def _get_objects_by_attribute(self, base_path, attributes, exact_text,
                                  sort_fields):
        """ The beets web-api accepts queries like:
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
            @type exact_text: bool
            @param sort_fields: fieldnames, each followed by '+' or '-'
            @type sort_fields: list of strings
            @rtype: list of json datasets describing tracks or albums
        """
        # assemble the query string
        query_parts = []
        # only used for 'exact_text'
        exact_query_list = []

        def quote_and_encode(text):
            # utf-8 seems to be necessary for Python 2.7 and urllib.quote
            if isinstance(text, unicode):
                text = text.encode('utf-8')
            elif isinstance(text, (int, float)):
                text = str(text)
            # Escape colons. The beets web API uses the colon to separate
            # field name and search term.
            text = text.replace(':', r'\:')
            # quoting for the query string
            return urllib.quote(text)

        for attribute in attributes:
            if isinstance(attribute, basestring):
                key = None
                value = quote_and_encode(attribute)
                query_parts.append(value)
                exact_query_list.append((None, attribute))
            else:
                # the beets API accepts upper and lower case, but always
                # returns lower case attributes
                key = quote_and_encode(attribute[0].lower())
                value = quote_and_encode(attribute[1])
                query_parts.append('{0}:{1}'.format(key, value))
                exact_query_list.append((attribute[0].lower(), attribute[1]))
        # add sorting fields
        for sort_field in (sort_fields or []):
            if (len(sort_field) > 1) and (sort_field[-1] in ('-', '+')):
                query_parts.append(quote_and_encode(sort_field))
            else:
                logger.info('Beets - invalid sorting field ignore: %s',
                            sort_field)
        query_string = '/'.join(query_parts)
        query_url = '{0}/query/{1}'.format(base_path, query_string)
        logger.debug('Beets query: %s', query_url)
        items = self._get(query_url)['results']
        if exact_text:
            # verify that text attributes do not just test 'is in', but match
            # equality
            for key, value in exact_query_list:
                if key is None:
                    # the value must match one of the item attributes
                    items = [item for item in items if value in item.values()]
                else:
                    # filtering is necessary only for text based attributes
                    if items and isinstance(items[0][key], basestring):
                        items = [item for item in items if item[key] == value]
        return items

    @cache()
    def get_artists(self):
        """ returns all artists of one or more tracks """
        names = self._get('/artist/')['artist_names']
        names.sort()
        # remove empty names
        return [name for name in names if name]

    def get_sorted_unique_track_attributes(self, field):
        sort_field = {'albumartist': 'albumartist_sort'}.get(field, field)
        return self._get_unique_attribute_values('/item', field, sort_field)

    def get_sorted_unique_album_attributes(self, field):
        sort_field = {'albumartist': 'albumartist_sort'}.get(field, field)
        return self._get_unique_attribute_values('/album', field, sort_field)

    @cache(ctl=32)
    def _get_unique_attribute_values(self, base_url, field, sort_field):
        """ returns all artists, genres, ... of tracks or albums """
        if not hasattr(self, "__legacy_beets_api_detected"):
            try:
                result = self._get('{0}/values/{1}?sort_key={2}'
                                   .format(base_url, field, sort_field),
                                   raise_not_found=True)
            except KeyError:
                # The above URL was added to the Beets API after v1.3.17
                # Probably we are working against an older version.
                logging.warning(
                    'Failed to use the /item/unique/KEY feature of the Beets '
                    'API (introduced after v1.3.17). Falling back to the '
                    'slower and more ressource intensive manual approach. '
                    'Please upgrade Beets, if possible.')
                # Warn only once and use the manual approach for all future
                # requests.
                self.__legacy_beets_api_detected = True
                # continue below with the fallback
            else:
                return result['values']
        # Fallback: use manual filtering (requires too much time and memory for
        # most collections).
        sorted_items = self._get('{0}/query/{1}+'
                                 .format(base_url, sort_field))['results']
        # extract the wanted field and remove all duplicates
        unique_values = []
        for item in sorted_items:
            value = item[field]
            if not unique_values or (value != unique_values[-1]):
                unique_values.append(value)
        return unique_values

    def get_track_stream_url(self, track_id):
        return '{0}/item/{1}/file'.format(self.api_endpoint, track_id)

    @cache(ctl=32)
    def get_album_art_url(self, album_id):
        # Sadly we cannot determine, if the Beets library really contains album
        # art. Thus we need to ask for it and check the status code.
        url = '{0}/album/{1}/art'.format(self.api_endpoint, album_id)
        try:
            request = urllib.urlopen(url)
        except IOError:
            # DNS problem or similar
            return None
        request.close()
        return url if request.getcode() == 200 else None

    def _get(self, url, raise_not_found=False):
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
            if (req.status_code == 404) and raise_not_found:
                # sometimes we need to distinguish between empty and "not found"
                raise KeyError("URL not found: %s" % url)
            else:
                return None
        else:
            return req.json()

    def _parse_multiple_albums(self, album_datasets):
        albums = []
        for dataset in (album_datasets or []):
            try:
                albums.append(parse_album(dataset, self))
            except (ValueError, KeyError) as exc:
                logger.info('Failed to parse album data: %s', exc)
        return [album for album in albums if album]

    def _parse_multiple_tracks(self, track_datasets):
        tracks = []
        for dataset in (track_datasets or []):
            try:
                tracks.append(parse_track(dataset, self))
            except (ValueError, KeyError) as exc:
                logger.info('Failed to parse track data: %s', exc)
        return [track for track in tracks if track]
