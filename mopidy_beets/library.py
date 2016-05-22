from __future__ import unicode_literals

import logging

from mopidy import backend, models
from mopidy.models import SearchResult

from .translator import assemble_uri, parse_uri


logger = logging.getLogger(__name__)


class AlbumsCategoryBrowser:

    field = None
    sort_fields = None
    label_fields = None

    def __init__(self, ref, api):
        self.ref = ref
        self.api = api

    def get_toplevel(self):
        keys = self.api.get_sorted_unique_album_attributes(self.field)
        return [models.Ref.directory(name=unicode(key), uri=assemble_uri(
            self.ref.uri, id_value=key)) for key in keys]

    def get_label(self, album):
        artist_names = [artist.name for artist in album.artists]
        if artist_names:
            return ' - '.join([' / '.join(artist_names), album.name])
        else:
            return album.name

    def get_directory(self, key):
        albums = self.api.get_albums_by([(self.field, key)], True,
                                        self.sort_fields)
        return [models.Ref.album(uri=album.uri, name=self.get_label(album))
                for album in albums]


class AlbumsByArtistBrowser(AlbumsCategoryBrowser):
    field = 'albumartist'
    sort_fields = ('original_year+', 'year+', 'album+')

    def get_label(self, album):
        return album.name


class AlbumsByGenreBrowser(AlbumsCategoryBrowser):
    field = 'genre'
    sort_fields = ('album+', )


class AlbumsByYearBrowser(AlbumsCategoryBrowser):
    field = 'year'
    sort_fields = ('month+', 'day+', 'album+')


class BeetsLibraryProvider(backend.LibraryProvider):

    root_directory = models.Ref.directory(uri='beets:library',
                                          name='Beets library')
    root_categorie_list = [
        ('albums-by-artist', 'Albums by Artist', AlbumsByArtistBrowser),
        ('albums-by-genre', 'Albums by Genre', AlbumsByGenreBrowser),
        ('albums-by-year', 'Albums by Year', AlbumsByYearBrowser),
    ]

    def __init__(self, *args, **kwargs):
        super(BeetsLibraryProvider, self).__init__(*args, **kwargs)
        self.remote = self.backend.beets_api
        self.category_browsers = []
        for key, label, browser_class in self.root_categorie_list:
            ref = models.Ref.directory(name=label, uri=assemble_uri(
                self.root_directory.uri, key))
            browser = browser_class(ref, self.remote)
            self.category_browsers.append(browser)

    def browse(self, uri):
        logger.debug('Browsing Beets at: %s', uri)
        parsed = parse_uri(uri, uri_prefix=self.root_directory.uri)
        if not parsed:
            logger.error('Beets - failed to parse uri: %s', uri)
            return []
        elif uri == self.root_directory.uri:
            # top level - show the categories
            refs = [browser.ref for browser in self.category_browsers]
            refs.sort(key=lambda item: item.name)
            return refs
        elif parsed[0] == 'album':
            # show an album
            try:
                album_id = parse_uri(uri, id_type=int)[1]
            except IndexError:
                logger.error('Beets - invalid album ID in URI: %s', uri)
                return []
            tracks = self.remote.get_tracks_by([('album_id', album_id)], True,
                                               ['track+'])
            return [models.Ref.track(uri=track.uri, name=track.name)
                    for track in tracks]
        else:
            # show a generic category directory
            parsed_uri, id_value = parse_uri(uri)
            for browser in self.category_browsers:
                if parsed_uri == browser.ref.uri:
                    if id_value is None:
                        return browser.get_toplevel()
                    else:
                        return browser.get_directory(parsed[1])
            else:
                logger.error('Invalid browse URI: %s / %s', uri, parsed[0])
                return []

    def search(self, query=None, uris=None, exact=False):
        # TODO: restrict the result to 'uris'
        logger.debug('Beets Query (exact=%s) within "%s": %s',
                     exact, uris, query)
        if not self.remote.has_connection:
            return []

        self._validate_query(query)
        search_list = []
        for (field, values) in query.items():
            for val in values:
                # missing / unsupported fields: uri, performer
                if field == 'any':
                    search_list.append(val)
                elif field == 'album':
                    search_list.append(('album', val))
                elif field == 'artist':
                    search_list.append(('artist', val))
                elif field == 'albumartist':
                    search_list.append(('albumartist', val))
                elif field == 'track_name':
                    search_list.append(('title', val))
                elif field == 'track_no':
                    search_list.append(('track', val))
                elif field == 'composer':
                    search_list.append(('composer', val))
                elif field == 'genre':
                    search_list.append(('genre', val))
                elif field == 'comment':
                    search_list.append(('comments', val))
                elif field == 'date':
                    # TODO: there is no 'date' in beets - just 'day', 'month'
                    #       and 'year'. Determine the format of 'date' and
                    #       define a suitable date format string?
                    search_list.append(('date', val))
                else:
                    logger.info('Beets: ignoring unknown query key: %s', field)
                    break
        logger.debug('Search query: %s', search_list)
        tracks = self.remote.get_tracks_by(search_list, exact, [])
        uri = '-'.join([item if isinstance(item, str) else '='.join(item)
                        for item in search_list])
        return SearchResult(uri='beets:search-' + uri, tracks=tracks)

    def lookup(self, uri=None, uris=None):
        logger.info('Beets lookup: %s', uri or uris)
        if uri:
            # the older method (mopidy < 1.0): return a list of tracks
            # handle one or more tracks given with multiple semicolons
            track_ids = uri.split(';')[1:]
            tracks = [self.remote.get_track(track_id, True)
                      for track_id in track_ids]
            # remove occourences of None
            return [track for track in tracks if track]
        else:
            # the newer method (mopidy >= 1.0): return a dict of uris and tracks
            return {uri: self.lookup(uri=uri) for uri in uris}

    def _validate_query(self, query):
        for values in query.values():
            if not values:
                raise LookupError('Missing query')
            for value in values:
                if not value:
                    raise LookupError('Missing query')
