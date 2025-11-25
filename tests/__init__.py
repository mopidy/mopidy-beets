import logging
import os
import unittest

from mopidy_beets.actor import BeetsBackend

TEST_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "data")


class MopidyBeetsTest(unittest.TestCase):
    @staticmethod
    def get_config():
        config = {}
        config["enabled"] = True
        config["hostname"] = "example.org"
        config["port"] = 8337
        return {"beets": config, "proxy": {}}

    def setUp(self):
        super().setUp()
        logging.getLogger("mopidy_beets.library").disabled = True
        config = self.get_config()
        self.backend = BeetsBackend(config=config, audio=None)
