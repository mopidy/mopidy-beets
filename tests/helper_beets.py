import collections
import logging
import os
import random
import threading
import time
import typing

import beets.test._common
import werkzeug.serving
from beets.util import bytestring_path
from beets.test.helper import TestHelper as BeetsTestHelper
from beetsplug.web import app as beets_web_app

from . import MopidyBeetsTest, TEST_DATA_DIRECTORY


BeetsTrack = collections.namedtuple(
    "BeetsTrack", ("title", "artist", "track"), defaults=(None, None)
)
BeetsAlbum = collections.namedtuple(
    "BeetsAlbum",
    ("title", "artist", "tracks", "genre", "year"),
    defaults=("", 0),
)


# Manipulate beets's ressource path before any action wants to access these files.
beets.test._common.RSRC = bytestring_path(
    os.path.abspath(os.path.join(TEST_DATA_DIRECTORY, "beets-rsrc"))
)


class BeetsLibrary(BeetsTestHelper):
    """Provide a temporary Beets library for testing against a real Beets web plugin."""

    def __init__(
        self,
        bind_host: str = "127.0.0.1",
        bind_port: typing.Optional[int] = None,
    ) -> None:
        self._app = beets_web_app
        # allow exceptions to propagate to the caller of the test client
        self._app.testing = True
        self._bind_host = bind_host
        if bind_port is None:
            self._bind_port = random.randint(10000, 32767)
        else:
            self._bind_port = bind_port
        self._server = None

        self.setup_beets(disk=True)
        self._app.config["lib"] = self.lib
        self.load_plugins("web")
        # prepare the server instance
        self._server = werkzeug.serving.make_server(
            self._bind_host, self._bind_port, self._app
        )
        self._server_thread = threading.Thread(target=self._server.serve_forever)

    def start(self):
        self._server_thread.start()
        # wait for the server to be ready
        while self._server is None:
            time.sleep(0.1)

    def stop(self):
        if self._server_thread is not None:
            self._server.shutdown()
            self._server_thread.join()
            self._server_thread = None

    def get_connection_pair(self):
        return (self._bind_host, self._bind_port)


class BeetsAPILibraryTest(MopidyBeetsTest):
    """Mixin for MopidyBeetsTest providing access to a temporary Beets library.

    Supported features:
    - import the albums defined in the 'BEETS_ALBUMS' class variable into the Beets
      library
    - accesses to `self.backend.library` will query the Beets library via the web plugin
    """

    BEETS_ALBUMS: list[BeetsAlbum] = []

    def setUp(self):
        logging.getLogger("beets").disabled = True
        logging.getLogger("werkzeug").disabled = True
        self.beets = BeetsLibrary()
        # set the host and port of the beets API in our class-based configuration
        config = self.get_config()
        host, port = self.beets.get_connection_pair()
        config["beets"]["hostname"] = host
        config["beets"]["port"] = port
        self.get_config = lambda: config
        # we call our parent initializer late, since we needed to adjust its config
        super().setUp()
        # Run the thread as late as possible in order to avoid hangs due to exceptions.
        # Such exceptions would cause `tearDown` to be skipped.
        self.beets.start()
        self.beets_populate()

    def beets_populate(self) -> None:
        """Import the albums specified in the class variable 'BEETS_ALBUMS'."""
        for album in self.BEETS_ALBUMS:
            album_items = []
            for track_index, track_data in enumerate(album.tracks):
                args = {
                    "album": album.title,
                    "albumartist": album.artist,
                    "genre": album.genre,
                    "artist": track_data.artist,
                    "title": track_data.title,
                    "track": track_data.track,
                    "year": album.year,
                }
                for key, fallback_value in {
                    "artist": album.artist,
                    "track": track_index,
                }.items():
                    if args[key] is None:
                        args[key] = fallback_value
                new_item = self.beets.add_item_fixture(**args)
                album_items.append(new_item)
            self.beets.lib.add_album(album_items)

    def tearDown(self):
        self.beets.stop()
