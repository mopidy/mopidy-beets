*********************
Release Documentation
*********************

The following steps are necessary for a release:

* Create a new changelog entry (README.rst)

* Update the release number in mopidy_beets/__init__.py

* Add a git tag: `git tag -a vX.Y.Z`

* Upload the source package to pypi: `python setup.py sdist upload`
