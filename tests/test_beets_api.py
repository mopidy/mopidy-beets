from typing import ClassVar

from .helper_beets import BeetsAlbum, BeetsAPILibraryTest, BeetsTrack


class LookupTest(BeetsAPILibraryTest):
    BEETS_ALBUMS: ClassVar[list[BeetsAlbum]] = [
        BeetsAlbum(
            "Album-Title-1",
            "Album-Artist-1",
            [
                BeetsTrack("Title-1"),
                BeetsTrack("Title-2"),
                BeetsTrack("Title-3"),
            ],
            "Genre-1",
            2012,
        ),
        BeetsAlbum(
            "Album-Title-2",
            "Album-Artist-2",
            [BeetsTrack("Title-1")],
        ),
    ]

    BROWSE_CATEGORIES = (
        "albums-by-artist",
        "albums-by-genre",
        "albums-by-year",
    )

    def get_uri(self, *components):
        return ":".join(("beets", "library", *components))

    def test_categories(self):
        response = self.backend.library.browse("beets:library")
        assert len(response) == len(self.BROWSE_CATEGORIES)
        for category in self.BROWSE_CATEGORIES:
            with self.subTest(category=category):
                full_category = self.get_uri(category)
                assert full_category in (item.uri for item in response)

    def test_browse_albums_by_artist(self):
        response = self.backend.library.browse("beets:library:albums-by-artist")
        expected_album_artists = sorted(album.artist for album in self.BEETS_ALBUMS)
        received_album_artists = [item.name for item in response]
        assert received_album_artists == expected_album_artists

    def test_browse_albums_by_genre(self):
        response = self.backend.library.browse("beets:library:albums-by-genre")
        expected_album_genres = sorted(album.genre for album in self.BEETS_ALBUMS)
        received_album_genres = [item.name for item in response]
        assert received_album_genres == expected_album_genres

    def test_browse_albums_by_year(self):
        response = self.backend.library.browse("beets:library:albums-by-year")
        expected_album_genres = sorted(str(album.year) for album in self.BEETS_ALBUMS)
        received_album_genres = [item.name for item in response]
        assert received_album_genres == expected_album_genres
