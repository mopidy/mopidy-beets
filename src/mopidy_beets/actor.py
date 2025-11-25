import logging
from typing import ClassVar

import pykka
from mopidy import backend
from mopidy.types import UriScheme

from .client import BeetsRemoteClient
from .library import BeetsLibraryProvider

logger = logging.getLogger(__name__)


class BeetsBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes: ClassVar[list[UriScheme]] = [UriScheme("beets")]

    def __init__(self, config, audio):
        super().__init__()

        beets_endpoint = (
            f"http://{config['beets']['hostname']}:{config['beets']['port']}"
        )

        self.beets_api = BeetsRemoteClient(beets_endpoint, config["proxy"])
        self.library = BeetsLibraryProvider(backend=self)
        self.playback = BeetsPlaybackProvider(audio=audio, backend=self)
        self.playlists = None


class BeetsPlaybackProvider(backend.PlaybackProvider):
    backend: BeetsBackend

    def translate_uri(self, uri):
        track_id = uri.split(";")[1]
        logger.debug(f"Getting info for track {uri} with id {track_id}")
        return self.backend.beets_api.get_track_stream_url(track_id)
