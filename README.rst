************
Mopidy-Beets
************

.. image:: https://img.shields.io/pypi/v/Mopidy-Beets.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Beets/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-Beets.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Beets/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/travis/mopidy/mopidy-beets/master.svg?style=flat
    :target: https://travis-ci.org/mopidy/mopidy-beets
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/mopidy/mopidy-beets/master.svg?style=flat
   :target: https://coveralls.io/r/mopidy/mopidy-beets?branch=master
   :alt: Test coverage

`Mopidy <http://www.mopidy.com/>`_ extension for browsing, searching and
playing music from `Beets <http://beets.io/>`_ via Beets' web extension.


Installation
============

Install by running::

    pip install Mopidy-Beets

Or, if available, install the Debian/Ubuntu package from `apt.mopidy.com
<http://apt.mopidy.com/>`_.


Configuration
=============

#. Setup the `Beets web plugin
   <http://beets.readthedocs.org/en/latest/plugins/web.html>`_.

#. Tell Mopidy where to find the Beets web interface by adding the following to
   your ``mopidy.conf``::

    [beets]
    hostname = 127.0.0.1
    port = 8888

#. Restart Mopidy.

#. Searches in Mopidy will now return results from your Beets library.

Proxy Configuration for OGG files (optional)
--------------------------------------------

You may want to configure an http proxy server in front of your beets
installation. Otherwise you could have problems with playing OGG files and
other formats that require seeking (in technical terms: support for http
"Range" requests is required for these files).

The following Nginx configuration snippet is sufficent::

    server {
        listen 127.0.0.1:8889;
        root /usr/share/beets/beetsplug/web;
        server_name beets.local;
        location / {
            proxy_pass http://localhost:8888;
            # this statement forces Nginx to emulate "Range" responses
            proxy_force_ranges on;
        }
    }

Now you should change the mopidy configuration accordingly to point to the
Nginx port above intead of the Beets port. Afterwards mopidy will be able to
play file formats that require seeking.


Usage
=====

#. Run ``beet web`` to start the Beets web interface.

#. Start Mopidy and access your Beets library via any Mopidy client:

   * Browse your collection by album

   * Search for tracks or albums

   * Let the music play!


Project resources
=================

- `Source code <https://github.com/mopidy/mopidy-beets>`_
- `Issue tracker <https://github.com/mopidy/mopidy-beets/issues>`_


Credits
=======

- Original author: `Janez Troha <https://github.com/dz0ny>`_
- Current maintainer: `Lars Kruse <devel@sumpfralle.de>`_
- `Contributors <https://github.com/mopidy/mopidy-beets/graphs/contributors>`_


Changelog
=========

v3.0.0 (UNRELEASED)
-------------------

- Support browsing albums by artist, genre and year

- Improved search (more categories, more precise)

- Align with Mopidy's current extension guidelines

v2.0.0 (2015-03-25)
-------------------

- Require Mopidy >= 1.0.

- Update to work with new playback API in Mopidy 1.0.

- Update to work with new backend search API in Mopidy 1.0.

v1.1.0 (2014-01-20)
-------------------

- Require Requests >= 2.0.

- Updated extension and backend APIs to match Mopidy 0.18.

v1.0.4 (2013-12-15)
-------------------

- Require Requests >= 1.0, as 0.x does not seem to be enough. (Fixes: #7)

- Remove hacks for Python 2.6 compatibility.

- Change search field ``track`` to ``track_name`` for compatibility with
  Mopidy 0.17. (Fixes: mopidy/mopidy#610)

v1.0.3 (2013-11-02)
-------------------

- Properly encode search queries containing non-ASCII chars.

- Rename logger to ``mopidy_beets``.

v1.0.2 (2013-04-30)
-------------------

- Fix search.

v1.0.1 (2013-04-28)
-------------------

- Initial release.
