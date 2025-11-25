import pathlib
from importlib.metadata import version

from mopidy import config, ext

__version__ = version("mopidy-beets")


class Extension(ext.Extension):
    dist_name = "mopidy-beets"
    ext_name = "beets"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()
        schema["hostname"] = config.Hostname()
        schema["port"] = config.Port()
        return schema

    def setup(self, registry):
        from mopidy_beets.actor import BeetsBackend  # noqa: PLC0415

        registry.add("backend", BeetsBackend)
