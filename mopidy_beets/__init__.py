from __future__ import unicode_literals

import os
from mopidy import ext, config
from mopidy.exceptions import ExtensionError


__doc__ = """A extension for playing music from Beets.

This extension handles URIs starting with ``beets:`` and enables you,
to play music from Beets web service.

See https://github.com/dz0ny/mopidy-beets/ for further instructions on
using this extension.

**Issues:**

https://github.com/dz0ny/mopidy-beets/issues

**Dependencies:**

requests

**Default config**

.. code-block:: ini

"""

__version__ = '1.0'


class BeetsExtension(ext.Extension):

    dist_name = 'Mopidy-Beets'
    ext_name = 'beets'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(BeetsExtension, self).get_config_schema()
        schema['hostname'] = config.String()
        return schema

    def validate_config(self, config):
        if not config.getboolean('beets', 'enabled'):
            return

    def validate_environment(self):
        try:
            import requests  # noqa
        except ImportError as e:
            raise ExtensionError('Library requests not found', e)

    def get_backend_classes(self):
        from .actor import BeetsBackend
        return [BeetsBackend]
