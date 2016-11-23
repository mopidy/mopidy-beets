*********************
Release Documentation
*********************

The following steps are necessary for a release:

* Create a new changelog entry (README.rst)

* Update the release number in mopidy_beets/__init__.py

* Create a relase commit: `git commit -m "Release vX.Y.Z"`

* Add a version tag to this commit: `git tag -a vX.Y.Z`

* Push the commit and the tag to the repository: `git push origin tag vX.Y.Z`

* Upload the source package to pypi: `python setup.py sdist && twine upload dist/Mopidy-Beets-X.Y.Z.tar.gz`
