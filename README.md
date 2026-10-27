# webchanges hard fork

This independently maintained fork integrates upstream v3.39.0 and all eight historical fork features. `main` owns source and release automation; edit source directly. Upstream updates are manual integrations, not automatic synchronization.

## Builds and releases

- Push to `main`: nightly wheel and sdist on [GitHub Releases](https://github.com/felixfoertsch/webchanges/releases). Release tag `nightly-<full commit SHA>` and package version `<application version>+nightly.<full commit SHA>` identify immutable source. Rebuilding that commit reuses its identity; existing bytes must match or publication stops.
- Push version tag `v<application version>` (for example `v3.39.0`): immutable stable GitHub release. Tag version must match `webchanges/__init__.py`.
- No fork packages publish to PyPI. Install downloaded fork wheels with `python -m pip install ./webchanges-<version>-py3-none-any.whl`.
- Builds run without write credentials. Separate publisher verifies source revision and artifact hashes; retries fill missing draft assets without replacing mismatched bytes.

Historical [patch-queue](https://github.com/felixfoertsch/webchanges/tree/patch-queue) remains preserved for provenance, not live source ownership. Integrated features: OpenAI-compatible AI differ, file-backed API keys, quiet change filtering, compact HTML digests, AI-failure suppression, actionable fetch errors, streamed newsletter summaries, and reasoning-effort forwarding.

The following upstream documentation is retained for reference; its upstream PyPI installation and release instructions do not describe this fork’s distribution.

------------------------------------------------------------------------

# webchanges [![PyPI downloads](https://img.shields.io/pypi/dm/webchanges.svg)](https://www.pepy.tech/project/webchanges)

**webchanges** *anonymously* checks web content (including images) and commands for changes, delivering instant notifications and AI-powered summaries to your favorite [platform](https://webchanges.readthedocs.io/en/stable/introduction.html#reporters).

## Highlights

- **Watch anything**: web pages (in a [real browser](https://webchanges.readthedocs.io/en/stable/jobs.html#use-browser) if needed), APIs, local files and command output.
- **Track only what matters** with over 30 [filters](https://webchanges.readthedocs.io/en/stable/filters.html).
- **Read changes at a glance** in formatted HTML, side by side, word by word, as [AI summaries](https://webchanges.readthedocs.io/en/stable/differs.html#ai-google-diff) and more.
- **Get notified anywhere**: email, Telegram, Discord, ntfy, webhooks and [more](https://webchanges.readthedocs.io/en/stable/reporters.html).
- **Few false alarms**: transient errors can be held back and repeated ones reported [once](https://webchanges.readthedocs.io/en/stable/jobs.html#suppress-repeated-errors).
- **Runs on your machine**, total privacy, no account needed, and extends with Python [hooks](https://webchanges.readthedocs.io/en/stable/hooks.html).

## Requirements

**webchanges** requires [![Supported Python versions](https://img.shields.io/pypi/pyversions/webchanges.svg)](https://www.python.org/downloads/). For the best experience, use the current version of [Python](https://www.python.org/downloads/); older Python versions are supported for 3 years after they're replaced. Free-threaded Python is supported.

For Generative AI summaries (BETA), you need a free [API Key from Google Cloud AI Studio](https://aistudio.google.com/app/apikey) (see [here](https://webchanges.readthedocs.io/en/stable/differs.html#ai-google-diff)).

## Installation

[![PyPI version](https://img.shields.io/pypi/v/webchanges.svg?label=)](https://pypi.org/project/webchanges/) [![Kit format](https://img.shields.io/pypi/format/webchanges.svg)](https://pypi.org/project/webchanges/) [![Package stability](https://img.shields.io/pypi/status/webchanges.svg)](https://pypi.org/project/webchanges/)

Install **webchanges** with [uv](https://docs.astral.sh/uv/) (recommended):

``` bash
uv pip install webchanges
```

or with `pip`:

``` bash
pip install webchanges
```

On Windows with Python 3.15, first run `set PYYAML_FORCE_LIBYAML=0` (in PowerShell: `$env:PYYAML_FORCE_LIBYAML = "0"`), as explained [here](https://webchanges.readthedocs.io/en/stable/introduction.html#install-windows).

### Other ways to run

- In a [Docker](https://www.docker.com/) container: a minimal implementation (no browser) is [here](https://github.com/yubiuser/webchanges-docker), and one with a browser is [here](https://github.com/jhedlund/webchanges-docker).
- As a [GitHub Action](https://docs.github.com/en/actions): an implementation is [here](https://github.com/swimmwatch/webchanges-action).

## Documentation [![Documentation status](https://img.shields.io/readthedocs/webchanges/stable.svg?label=)](https://webchanges.readthedocs.io/)

The documentation is hosted on [Read the Docs](https://webchanges.readthedocs.io/).

## Quick Start

### Initialize

1.  Run the following command to create the default `config.yaml` (configuration) and `jobs.yaml` (jobs) files and open an editor to add your [jobs](https://webchanges.readthedocs.io/en/stable/jobs.html):

    ``` bash
    webchanges --edit-jobs
    ```

2.  Run the following command to change the default [configuration](https://webchanges.readthedocs.io/en/stable/configuration.html), e.g. to receive change notifications ("\`reports \<https://webchanges.readthedocs.io/en/stable/reporters.html\>\`\_\_") by [email](https://webchanges.readthedocs.io/en/stable/reporters.html#smtp) and/or one of many other methods:

    ``` bash
    webchanges --edit-config
    ```

### Run

To check the sources in your jobs and report on (e.g. display or via email) any changes found from the last time the program ran, just run:

``` bash
webchanges
```

### Schedule

**webchanges** leverages the power of a system scheduler:

- On Linux you can use cron, with the help of a tool like [crontab.guru](https://crontab.guru) (help [here](https://www.computerhope.com/unix/ucrontab.htm));
- On Windows you can use [Windows Task Scheduler](https://en.wikipedia.org/wiki/Windows_Task_Scheduler);
- On macOS you can use [launchd](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html) (help [here](https://launchd.info/)).

## Code

[![Code coverage by Coveralls](https://img.shields.io/coverallsCoverage/github/mborsetti/webchanges.svg)](https://coveralls.io/github/mborsetti/webchanges?branch=main) [![Issues at https://github.com/mborsetti/webchanges/issues](https://img.shields.io/github/issues-raw/mborsetti/webchanges)](https://github.com/mborsetti/webchanges/issues) [![Code style ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

The code, issues tracker, and discussions are hosted on [GitHub](https://github.com/mborsetti/webchanges).

## Contributing

We welcome any contribution no matter how small, both as pull requests or [issue reports](https://github.com/mborsetti/webchanges/issues).

More information for code and documentation contributors is [here](https://webchanges.readthedocs.io/en/stable/contributing.html), and our wishlist is [here](https://github.com/mborsetti/webchanges/blob/main/WISHLIST.md).

## License

[![License at https://pypi.org/project/webchanges/](https://img.shields.io/pypi/l/webchanges.svg)](https://pypi.org/project/webchanges/)

See the [complete licenses](https://raw.githubusercontent.com/mborsetti/webchanges/refs/heads/main/LICENSE.md) (released under the [MIT License](https://opensource.org/licenses/MIT) but redistributing modified source code, dated 30 July 2020, from [urlwatch 2.21](https://github.com/thp/urlwatch/tree/346b25914b0418342ffe2fb0529bed702fddc01f) licensed under a [BSD 3-Clause License](https://raw.githubusercontent.com/thp/urlwatch/346b25914b0418342ffe2fb0529bed702fddc01f/COPYING)).

## Relationship with **urlwatch**

This project is a fork of [urlwatch 2.21](https://github.com/thp/urlwatch/tree/346b25914b0418342ffe2fb0529bed702fddc01f) and has since added many features; see the [comparison](https://webchanges.readthedocs.io/en/stable/upgrading.html).
