from __future__ import unicode_literals

import logging
import pykka

from mopidy.backends import base

from .library import BeetsLibraryProvider
from .client import BeetsRemoteClient

logger = logging.getLogger('mopidy.backends.beets')


class BeetsBackend(pykka.ThreadingActor, base.Backend):

    def __init__(self, config, audio):
        super(BeetsBackend, self).__init__()
        self.beets_api = BeetsRemoteClient(config['beets']['hostname'])
        self.library = BeetsLibraryProvider(backend=self)
        self.playback = BeetsPlaybackProvider(audio=audio, backend=self)
        self.playlists = None

        self.uri_schemes = ['beets']


class BeetsPlaybackProvider(base.BasePlaybackProvider):

    def play(self, track):
        id = track.uri.split(';')[1]
        logger.info('Getting info for track %s with id %s' % (track.uri, id))
        track = self.backend.beets_api.get_track(id, True)
        return super(BeetsPlaybackProvider, self).play(track)
