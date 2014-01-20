from __future__ import unicode_literals

import logging
import pykka

from mopidy import backend

from .library import BeetsLibraryProvider
from .client import BeetsRemoteClient

logger = logging.getLogger(__name__)


class BeetsBackend(pykka.ThreadingActor, backend.Backend):

    def __init__(self, config, audio):
        super(BeetsBackend, self).__init__()

        beets_endpoint = 'http://%s:%s' % (
            config['beets']['hostname'], config['beets']['port'])

        self.beets_api = BeetsRemoteClient(beets_endpoint)
        self.library = BeetsLibraryProvider(backend=self)
        self.playback = BeetsPlaybackProvider(audio=audio, backend=self)
        self.playlists = None

        self.uri_schemes = ['beets']


class BeetsPlaybackProvider(backend.PlaybackProvider):

    def play(self, track):
        id = track.uri.split(';')[1]
        logger.info('Getting info for track %s with id %s' % (track.uri, id))
        track = self.backend.beets_api.get_track(id, True)
        return super(BeetsPlaybackProvider, self).play(track)
