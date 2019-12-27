*********
Changelog
*********


v4.0.0rc1 (2019-12-27)
======================

- Require Mopidy >= 3.0.0a3.

- Require Python >= 3.7. No major changes required.

- Update project setup.

- Change default port from 8888 to 8337 to match Beets' defaults.


v3.1.0 (2016-11-23)
===================

- Fix handling of non-ascii characters in album titles and artist names

- Fix handling of empty titles and names

- Reduce ressource consumption of string matching API requests


v3.0.0 (2016-05-28)
===================

- Support browsing albums by artist, genre and year

- Improved search (more categories, more precise)

- Align with Mopidy's current extension guidelines


v2.0.0 (2015-03-25)
===================

- Require Mopidy >= 1.0.

- Update to work with new playback API in Mopidy 1.0.

- Update to work with new backend search API in Mopidy 1.0.


v1.1.0 (2014-01-20)
===================

- Require Requests >= 2.0.

- Updated extension and backend APIs to match Mopidy 0.18.


v1.0.4 (2013-12-15)
===================

- Require Requests >= 1.0, as 0.x does not seem to be enough. (Fixes: #7)

- Remove hacks for Python 2.6 compatibility.

- Change search field ``track`` to ``track_name`` for compatibility with
  Mopidy 0.17. (Fixes: mopidy/mopidy#610)


v1.0.3 (2013-11-02)
===================

- Properly encode search queries containing non-ASCII chars.

- Rename logger to ``mopidy_beets``.


v1.0.2 (2013-04-30)
===================

- Fix search.


v1.0.1 (2013-04-28)
===================

- Initial release.
