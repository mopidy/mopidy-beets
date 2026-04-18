from __future__ import annotations

from typing import ClassVar, override

from mopidy.models import Album, Ref

from mopidy_beets.browsers import GenericBrowserBase
from mopidy_beets.translator import assemble_uri


class AlbumsCategoryBrowser(GenericBrowserBase):
    field: ClassVar[str]
    sort_fields: ClassVar[tuple[str, ...]]

    def get_toplevel(self) -> list[Ref]:
        keys = self.api.get_sorted_unique_album_attributes(self.field)
        return [
            Ref.directory(
                name=str(k),
                uri=assemble_uri(self.ref.uri, id_value=k),
            )
            for k in sorted(keys)
        ]

    def get_directory(self, key) -> list[Ref]:
        albums = self.api.get_albums_by(
            [(self.field, key)],
            exact_text=True,
            sort_fields=self.sort_fields,
        )
        return [
            Ref.album(
                uri=a.uri,
                name=self._get_label(a),
            )
            for a in albums
            if a.uri is not None
        ]

    def _get_label(self, album: Album) -> str | None:
        raise NotImplementedError


class AlbumsByArtistBrowser(AlbumsCategoryBrowser):
    field = "albumartist"
    sort_fields = ("original_year+", "year+", "album+")

    @override
    def _get_label(self, album: Album) -> str | None:
        return album.name


class AlbumsByGenreBrowser(AlbumsCategoryBrowser):
    field = "genre"
    sort_fields = ("albumartist", "original_year+", "year+", "album+")

    @override
    def _get_label(self, album: Album) -> str | None:
        artists = " / ".join([a.name for a in album.artists if a.name is not None])
        if artists and album.date:
            return f"{artists} - {album.name} ({album.date.split('-')[0]})"
        if artists:
            return f"{artists} - {album.name}"
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

    @override
    def _get_label(self, album: Album) -> str | None:
        artists = " / ".join([a.name for a in album.artists if a.name is not None])
        if artists:
            return f"{artists} - {album.name}"
        return album.name
