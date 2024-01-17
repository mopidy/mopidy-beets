from unittest import mock

from mopidy_beets import BeetsExtension
from mopidy_beets.actor import BeetsBackend

from . import MopidyBeetsTest


class ExtensionTest(MopidyBeetsTest):
    def test_get_default_config(self):
        ext = BeetsExtension()

        config = ext.get_default_config()

        self.assertIn("[beets]", config)
        self.assertIn("enabled = true", config)
        self.assertIn("hostname = 127.0.0.1", config)
        self.assertIn("port = 8337", config)

    def test_get_config_schema(self):
        ext = BeetsExtension()

        schema = ext.get_config_schema()

        self.assertIn("enabled", schema)
        self.assertIn("hostname", schema)
        self.assertIn("port", schema)

    def test_get_backend_classes(self):
        registry = mock.Mock()
        ext = BeetsExtension()
        ext.setup(registry)
        self.assertIn(
            mock.call("backend", BeetsBackend), registry.add.mock_calls
        )

    def test_init_backend(self):
        backend = BeetsBackend(self.get_config(), None)
        self.assertIsNotNone(backend)
        backend.on_start()
        backend.on_stop()
