Mopidy-Beets
============

`Mopidy <http://www.mopidy.com/>`_ extension for playing music from
`Beets <http://beets.radbox.org/>`_ via Beets' web extension.

Usage
-----

#. Setup the `Beets web plugin
   <http://beets.readthedocs.org/en/latest/plugins/web.html>`_.

#. Install the Mopidy-Beets extension by running::

    sudo pip install mopidy-beets

#. Tell Mopidy where to find the Beets web interface by adding the following to
   your ``mopidy.conf``::

    [beets]
    host = "http://yourserver:port"

#. Restart Mopidy.

#. Searches in Mopidy will now return results from your Beets library.


Project resources
-----------------

- `Source code <https://github.com/dz0ny/mopidy-beets>`_
- `Issue tracker <https://github.com/mopidy/mopidy-beets/issues>`_
- `Download development snapshot
  <https://github.com/dz0ny/mopidy-beets/tarball/develop#egg=mopidy-beets-dev>`_
