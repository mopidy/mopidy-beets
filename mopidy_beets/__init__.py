import os

import pkg_resources
from mopidy import config, ext


__version__ = pkg_resources.get_distribution("Mopidy-Beets").version


class BeetsExtension(ext.Extension):
    dist_name = "Mopidy-Beets"
    ext_name = "beets"
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), "ext.conf")
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super().get_config_schema()
        schema["hostname"] = config.Hostname()
        schema["port"] = config.Port()
        return schema

    def setup(self, registry):
        from .actor import BeetsBackend

        registry.add("backend", BeetsBackend)
