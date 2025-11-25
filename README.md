# mopidy-beets

[![Latest PyPI version](https://img.shields.io/pypi/v/mopidy-beets)](https://pypi.org/p/mopidy-beets)
[![CI build status](https://img.shields.io/github/actions/workflow/status/mopidy/mopidy-beets/ci.yml)](https://github.com/mopidy/mopidy-beets/actions/workflows/ci.yml)
[![Test coverage](https://img.shields.io/codecov/c/gh/mopidy/mopidy-beets)](https://codecov.io/gh/mopidy/mopidy-beets)

[Mopidy](https://mopidy.com/) extension for playing music from a music collection managed via [Beets](https://beets.io/).
This extension uses the
[Beets plugin "web"](https://beets.readthedocs.io/en/latest/plugins/web.html).


## Installation

Install by running:

```sh
python3 -m pip install mopidy-beets
```

See https://mopidy.com/ext/beets/ for alternative installation methods.


## Configuration

1. Setup the [Beets plugin
   "web"](https://beets.readthedocs.io/en/latest/plugins/web.html).

2. Tell Mopidy where to find the Beets web interface by adding the following to
   your `mopidy.conf`:

   ```ini
   [beets]
   hostname = 127.0.0.1
   port = 8337
   ```
   
3. Restart Mopidy.

The Beets library is now accessible in the "browser" section of your Mopidy
client. Additional searches in Mopidy return results from your Beets library.


### Proxy configuration for OGG files (optional)

In case you use a Beets version older than 1.6.1, you may need to configure
an HTTP reverse-proxy server in front of the Beets web plugin (not Mopidy)
because `it does not handle HTTP "Range" requests properly
<https://github.com/beetbox/beets/pull/5057>`_.

If you don't apply this workaround, Mopidy may not be able to stream/play
large audio files and/or does not allow you to seek.
The is the case for OGG files in particular.

The following Nginx configuration snippet is sufficient:

```
server {
    listen 127.0.0.1:8338;
    root /usr/share/beets/beetsplug/web;
    server_name beets.local;
    location / {
        proxy_pass http://localhost:8337;
        # this statement forces Nginx to emulate "Range" responses
        proxy_force_ranges on;
        # Hide Range header from beets/flask, preventing range handling
        proxy_set_header "Range" "";
    }
}
```

Now you should change the Mopidy configuration accordingly to point to the
Nginx port above instead of the Beets port. Afterwards Mopidy will be able to
play file formats that require seeking.


## Usage

1. Run `beet web` to start the Beets web interface.

2. Start Mopidy and access your Beets library via any Mopidy client:

   - Browse your collection by album
   - Search for tracks or albums
   - Let the music play!


## Project resources

- [Source code](https://github.com/mopidy/mopidy-beets)
- [Issues](https://github.com/mopidy/mopidy-beets/issues)
- [Releases](https://github.com/mopidy/mopidy-beets/releases)


## Development

### Set up development environment

Clone the repo using, e.g. using [gh](https://cli.github.com/):

```sh
gh repo clone mopidy/mopidy-beets
```

Enter the directory, and install dependencies using [uv](https://docs.astral.sh/uv/):

```sh
cd mopidy-beets/
uv sync
```

### Running tests

To run all tests and linters in isolated environments, use
[tox](https://tox.wiki/):

```sh
tox
```

To only run tests, use [pytest](https://pytest.org/):

```sh
pytest
```

To format the code, use [ruff](https://docs.astral.sh/ruff/):

```sh
ruff format .
```

To check for lints with ruff, run:

```sh
ruff check .
```

To check for type errors, use [pyright](https://microsoft.github.io/pyright/):

```sh
pyright .
```


### Making a release

To make a release to PyPI, go to the project's [GitHub releases
page](https://github.com/mopidy/mopidy-beets/releases)
and click the "Draft a new release" button.

In the "choose a tag" dropdown, select the tag you want to release or create a
new tag, e.g. `v0.1.0`. Add a title, e.g. `v0.1.0`, and a description of the changes.

Decide if the release is a pre-release (alpha, beta, or release candidate) or
should be marked as the latest release, and click "Publish release".

Once the release is created, the `release.yml` GitHub Action will automatically
build and publish the release to
[PyPI](https://pypi.org/project/mopidy-beets/).


## Credits

- Original author: [Janez Troha](https://github.com/dz0ny)
- Current maintainer: [Lars Kruse](https://github.com/sumpfralle)
- [Contributors](https://github.com/mopidy/mopidy-beets/graphs/contributors)
