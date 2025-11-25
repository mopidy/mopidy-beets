from unittest import mock

from mopidy_beets import Extension
from mopidy_beets.actor import BeetsBackend

from . import MopidyBeetsTest


class ExtensionTest(MopidyBeetsTest):
    def test_get_default_config(self):
        ext = Extension()

        config = ext.get_default_config()

        assert "[beets]" in config
        assert "enabled = true" in config
        assert "hostname = 127.0.0.1" in config
        assert "port = 8337" in config

    def test_get_config_schema(self):
        ext = Extension()

        schema = ext.get_config_schema()

        assert "enabled" in schema
        assert "hostname" in schema
        assert "port" in schema

    def test_get_backend_classes(self):
        registry = mock.Mock()
        ext = Extension()
        ext.setup(registry)
        assert mock.call("backend", BeetsBackend) in registry.add.mock_calls

    def test_init_backend(self):
        backend = BeetsBackend(self.get_config(), None)
        assert backend is not None
        backend.on_start()
        backend.on_stop()
