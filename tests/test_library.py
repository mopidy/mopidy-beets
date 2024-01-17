from . import MopidyBeetsTest


class LibraryTest(MopidyBeetsTest):
    def test_invalid_uri(self):
        refs = self.backend.library.lookup("beets:invalid_uri")
        self.assertEqual(refs, [])
