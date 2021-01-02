************
Mopidy-Beets
************

.. image:: https://img.shields.io/pypi/v/Mopidy-Beets
    :target: https://pypi.org/project/Mopidy-Beets/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/github/workflow/status/mopidy/mopidy-beets/CI
    :target: https://github.com/mopidy/mopidy-beets/actions
    :alt: CI build status

.. image:: https://img.shields.io/codecov/c/gh/mopidy/mopidy-beets
    :target: https://codecov.io/gh/mopidy/mopidy-beets
    :alt: Test coverage

`Mopidy <https://mopidy.com/>`_ extension for browsing, searching and
playing music from `Beets <https://beets.io/>`_ via Beets' web extension.


Installation
============

Install by running::

    sudo python3 -m pip install Mopidy-Beets

See https://mopidy.com/ext/beets/ for alternative installation methods.


Configuration
=============

#. Setup the `Beets web plugin
   <https://beets.readthedocs.org/en/latest/plugins/web.html>`_.

#. Tell Mopidy where to find the Beets web interface by adding the following to
   your ``mopidy.conf``::

    [beets]
    hostname = 127.0.0.1
    port = 8337

#. Restart Mopidy.

#. The Beets library is now accessible in the "browser" section of your Mopidy
   client. Additionally searches in Mopidy return results from your Beets
   library.

Proxy configuration for OGG files (optional)
--------------------------------------------

You may want to configure an http proxy server in front of your Beets plugin
(not mopidy). Otherwise you could have problems with playing OGG files and
other formats that require seeking (in technical terms: support for http
"Range" requests is required for these files).

The following Nginx configuration snippet is sufficient::

    server {
        listen 127.0.0.1:8338;
        root /usr/share/beets/beetsplug/web;
        server_name beets.local;
        location / {
            proxy_pass http://localhost:8337;
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
- `Changelog <https://github.com/mopidy/mopidy-beets/releases>`_


Credits
=======

- Original author: `Janez Troha <https://github.com/dz0ny>`_
- Current maintainer: `Lars Kruse <devel@sumpfralle.de>`_
- `Contributors <https://github.com/mopidy/mopidy-beets/graphs/contributors>`_
