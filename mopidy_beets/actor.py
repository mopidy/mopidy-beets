from __future__ import unicode_literals

import logging

from mopidy import backend

import pykka

from .client import BeetsRemoteClient
from .library import BeetsLibraryProvider


logger = logging.getLogger(__name__)


class BeetsBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ['beets']

    def __init__(self, config, audio):
        super(BeetsBackend, self).__init__()

        beets_endpoint = 'http://%s:%s' % (
            config['beets']['hostname'], config['beets']['port'])

        self.beets_api = BeetsRemoteClient(beets_endpoint, config['proxy'])
        self.library = BeetsLibraryProvider(backend=self)
        self.playback = BeetsPlaybackProvider(audio=audio, backend=self)
        self.playlists = None


class BeetsPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        track_id = uri.split(';')[1]
        logger.debug('Getting info for track %s with id %s' % (uri, track_id))
        return self.backend.beets_api.get_track_stream_url(track_id)
