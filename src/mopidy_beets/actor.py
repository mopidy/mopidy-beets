from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, override

import pykka
from mopidy import backend
from mopidy.types import Uri, UriScheme

from .client import BeetsRemoteClient
from .library import BeetsLibraryProvider

if TYPE_CHECKING:
    from mopidy.audio import AudioProxy
    from mopidy.config import Config

logger = logging.getLogger(__name__)


class BeetsBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes: ClassVar[list[UriScheme]] = [UriScheme("beets")]

    @override
    def __init__(self, *, config: Config, audio: AudioProxy) -> None:
        super().__init__(config=config, audio=audio)

        beets_endpoint = (
            f"http://{config['beets']['hostname']}:{config['beets']['port']}"
        )

        self.beets_api = BeetsRemoteClient(beets_endpoint, config["proxy"])
        self.library = BeetsLibraryProvider(backend=self)
        self.playback = BeetsPlaybackProvider(audio=audio, backend=self)
        self.playlists = None


class BeetsPlaybackProvider(backend.PlaybackProvider):
    backend: BeetsBackend

    @override
    def translate_uri(self, uri: Uri) -> Uri | None:
        track_id = uri.split(";")[1]
        logger.debug(f"Getting info for track {uri} with id {track_id}")
        return self.backend.beets_api.get_track_stream_url(track_id)
