from mopidy import models

from mopidy_beets.browsers import GenericBrowserBase
from mopidy_beets.translator import assemble_uri


class AlbumsCategoryBrowser(GenericBrowserBase):
    field = None
    sort_fields = None
    label_fields = None

    def get_toplevel(self):
        keys = self.api.get_sorted_unique_album_attributes(self.field)
        return [
            models.Ref.directory(
                name=str(key), uri=assemble_uri(self.ref.uri, id_value=key)
            )
            for key in keys
        ]

    def get_directory(self, key):
        albums = self.api.get_albums_by([(self.field, key)], True, self.sort_fields)
        return [
            models.Ref.album(uri=album.uri, name=self._get_label(album))
            for album in albums
        ]


class AlbumsByArtistBrowser(AlbumsCategoryBrowser):
    field = "albumartist"
    sort_fields = ("original_year+", "year+", "album+")

    def _get_label(self, album):
        return album.name


class AlbumsByGenreBrowser(AlbumsCategoryBrowser):
    field = "genre"
    sort_fields = ("albumartist", "original_year+", "year+", "album+")

    def _get_label(self, album):
        artists = " / ".join([artist.name for artist in album.artists])
        if artists and album.date:
            return "{0} - {1} ({2})".format(
                artists, album.name, album.date.split("-")[0]
            )
        elif artists:
            return "{0} - {1}".format(artists, album.name)
        else:
            return album.name


class AlbumsByYearBrowser(AlbumsCategoryBrowser):
    field = "year"
    sort_fields = (
        "original_month+",
        "original_day+",
        "month+",
        "day+",
        "album+",
    )

    def _get_label(self, album):
        artists = " / ".join([artist.name for artist in album.artists])
        if artists:
            return "{0} - {1}".format(artists, album.name)
        else:
            return album.name
