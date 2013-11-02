from __future__ import unicode_literals

import unittest

from mopidy_beets import BeetsExtension


class ExtensionTest(unittest.TestCase):

    def test_get_default_config(self):
        ext = BeetsExtension()

        config = ext.get_default_config()

        self.assertIn('[beets]', config)
        self.assertIn('enabled = true', config)
        self.assertIn('hostname = 127.0.0.1', config)
        self.assertIn('port = 8888', config)

    def test_get_config_schema(self):
        ext = BeetsExtension()

        schema = ext.get_config_schema()

        self.assertIn('enabled', schema)
        self.assertIn('hostname', schema)
        self.assertIn('port', schema)

    # TODO Write more tests
