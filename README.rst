************
Mopidy-Beets
************

.. image:: https://img.shields.io/pypi/v/Mopidy-Beets
    :target: https://pypi.python.org/pypi/Mopidy-Beets/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/circleci/build/gh/mopidy/mopidy-beets
    :target: https://img.shields.io/circleci/build/gh/mopidy/mopidy-beets
    :alt: CircleCI build status

.. image:: https://img.shields.io/codecov/c/gh/mopidy/mopidy-beets
   :target: https://codecov.io/gh/mopidy/mopidy-beets
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
    port = 8337

#. Restart Mopidy.

#. The Beets library is now accessible in the "browser" section of your Mopidy
   client. Additionally searches in Mopidy return results from your Beets
   library.

Proxy Configuration for OGG files (optional)
--------------------------------------------

You may want to configure an http proxy server in front of your Beets plugin
(not mopidy). Otherwise you could have problems with playing OGG files and
other formats that require seeking (in technical terms: support for http
"Range" requests is required for these files).

The following Nginx configuration snippet is sufficient::

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
Nginx port above instead of the Beets port. Afterwards mopidy will be able to
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

See the [CHANGELOG file](./CHANGELOG.rst) for details.
