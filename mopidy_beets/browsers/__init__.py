class GenericBrowserBase:
    def __init__(self, ref, api):
        self.ref = ref
        self.api = api

    def get_toplevel(self):
        """ deliver the top level directories or tracks for this browser

        The result is a list of ``mopidy.models.Ref`` objects.
        Usually this list contains entries like "genre" or other categories.
        """
        raise NotImplementedError

    def get_directory(self, key):
        """ deliver the corresponding sub items for a given category key

        The result is a list of ``mopidy.models.Ref`` objects.
        Usually this list contains tracks or albums belonging to the given
        category 'key'.
        """
        raise NotImplementedError
