************
Mopidy-Beets
************

.. image:: https://pypip.in/v/Mopidy-Beets/badge.png
    :target: https://crate.io/packages/Mopidy-Beets/
    :alt: Latest PyPI version

.. image:: https://pypip.in/d/Mopidy-Beets/badge.png
    :target: https://crate.io/packages/Mopidy-Beets/
    :alt: Number of PyPI downloads

.. image:: https://travis-ci.org/mopidy/mopidy-beets.png?branch=master
    :target: https://travis-ci.org/mopidy/mopidy-beets
    :alt: Travis CI build status

.. image:: https://coveralls.io/repos/mopidy/mopidy-beets/badge.png?branch=master
   :target: https://coveralls.io/r/mopidy/mopidy-beets?branch=master
   :alt: Test coverage

`Mopidy <http://www.mopidy.com/>`_ extension for playing music from
`Beets <http://beets.radbox.org/>`_ via Beets' web extension.


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


Project resources
=================

- `Source code <https://github.com/mopidy/mopidy-beets>`_
- `Issue tracker <https://github.com/mopidy/mopidy-beets/issues>`_
- `Download development snapshot
  <https://github.com/mopidy/mopidy-beets/tarball/master#egg=Mopidy-Beets-dev>`_


Changelog
=========

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
