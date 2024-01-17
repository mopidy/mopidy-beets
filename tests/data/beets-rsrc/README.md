# Minimal replication of beets' ressource directory

The `BeetsHelper.add_fixture` method relies on a file named `min.mp3` to exist in the
*beets* ressource directory.
By default *beets* assumes its ressource directory to be located right below the `test/`
directory in the *beets* repository.
But this path is not part of the *beets* package.
Thus, we add the minimal amount of necessary files and manipulate the location stored in
`beets.test._common.RSRC`.
