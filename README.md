This fork follows upstream [webchanges](https://github.com/mborsetti/webchanges) with ordered patches [0001](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0001-add-OpenAI-compatible-AI-differ-with-email-integration-coverage.patch), [0002](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0002-support-file-backed-AI-API-keys.patch), [0003](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0003-support-quiet-AI-change-filtering.patch), [0004](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0004-add-compact-HTML-change-digests.patch), [0005](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0005-suppress-AI-failures-from-change-reports.patch), [0006](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0006-show-actionable-fetch-errors-after-digest-content.patch), [0007](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0007-handle-streamed-newsletter-summaries-reject-silent-failures.patch), [0008](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0008-forward-reasoning-effort-to-OpenAI-compatible-models.patch). `patch-queue` owns workflows and patches; generated `main` contains upstream source plus all patches. Stable builds follow upstream releases; nightly builds follow upstream default branch.

# Patched webchanges

Applied patches, oldest first:

1.  [0001-add-OpenAI-compatible-AI-differ-with-email-integration-coverage.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0001-add-OpenAI-compatible-AI-differ-with-email-integration-coverage.patch)
2.  [0002-support-file-backed-AI-API-keys.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0002-support-file-backed-AI-API-keys.patch)
3.  [0003-support-quiet-AI-change-filtering.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0003-support-quiet-AI-change-filtering.patch)
4.  [0004-add-compact-HTML-change-digests.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0004-add-compact-HTML-change-digests.patch)
5.  [0005-suppress-AI-failures-from-change-reports.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0005-suppress-AI-failures-from-change-reports.patch)
6.  [0006-show-actionable-fetch-errors-after-digest-content.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0006-show-actionable-fetch-errors-after-digest-content.patch)
7.  [0007-handle-streamed-newsletter-summaries-reject-silent-failures.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0007-handle-streamed-newsletter-summaries-reject-silent-failures.patch)
8.  [0008-forward-reasoning-effort-to-OpenAI-compatible-models.patch](https://github.com/felixfoertsch/webchanges/blob/patch-queue/patches/0008-forward-reasoning-effort-to-OpenAI-compatible-models.patch)

------------------------------------------------------------------------

# webchanges [![PyPI downloads](https://img.shields.io/pypi/dm/webchanges.svg)](https://www.pepy.tech/project/webchanges)

**webchanges** *anonymously* checks web content (including images) and commands for changes, delivering instant notifications and AI-powered summaries to your favorite [platform](https://webchanges.readthedocs.io/en/stable/introduction.html#reporters).

## Highlights

- **AI-powered change summaries** via Gemini ([ai_google differ](https://webchanges.readthedocs.io/en/stable/differs.html#ai-google-diff), BETA).
- **Structural diffs for JSON and XML** via the [deepdiff differ](https://webchanges.readthedocs.io/en/stable/differs.html#deepdiff-diff).
- **Visual diffs for images** via the [image differ](https://webchanges.readthedocs.io/en/stable/differs.html#image-diff) (BETA).
- **Bypass TLS/JA3 fingerprinting** with the optional [curl_cffi](https://webchanges.readthedocs.io/en/stable/jobs.html#http-client) HTTP client.
- **JSON-Schema-validated** `jobs.yaml` and `config.yaml` for editor autocompletion and inline validation.

## Requirements

**webchanges** requires [![Supported Python versions](https://img.shields.io/pypi/pyversions/webchanges.svg)](https://www.python.org/downloads/). For the best experience, use the current version of [Python](https://www.python.org/downloads/); older Python versions are supported for 3 years after they're replaced. Free-threaded Python is supported, though some optional dependencies may not be.

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

[![Code coverage by Coveralls](https://img.shields.io/coverallsCoverage/github/mborsetti/webchanges.svg)](https://coveralls.io/github/mborsetti/webchanges?branch=main) [![Issues at https://github.com/mborsetti/webchanges/issues](https://img.shields.io/github/issues-raw/mborsetti/webchanges)](https://github.com/mborsetti/webchanges/issues) [![Code style ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff) [![OpenSSF Scoreard](https://api.scorecard.dev/projects/github.com/mborsetti/webchanges/badge)](https://scorecard.dev/viewer/?uri=github.com/mborsetti/webchanges)

The code, issues tracker, and discussions are hosted on [GitHub](https://github.com/mborsetti/webchanges).

## Contributing

We welcome any contribution no matter how small, both as pull requests or [issue reports](https://github.com/mborsetti/webchanges/issues).

More information for code and documentation contributors is [here](https://webchanges.readthedocs.io/en/stable/contributing.html), and our wishlist is [here](https://github.com/mborsetti/webchanges/blob/main/WISHLIST.md).

## License

[![License at https://pypi.org/project/webchanges/](https://img.shields.io/pypi/l/webchanges.svg)](https://pypi.org/project/webchanges/)

See the [complete licenses](https://raw.githubusercontent.com/mborsetti/webchanges/refs/heads/main/LICENSE.md) (released under the [MIT License](https://opensource.org/licenses/MIT) but redistributing modified source code, dated 30 July 2020, from [urlwatch 2.21](https://github.com/thp/urlwatch/tree/346b25914b0418342ffe2fb0529bed702fddc01f) licensed under a [BSD 3-Clause License](https://raw.githubusercontent.com/thp/urlwatch/346b25914b0418342ffe2fb0529bed702fddc01f/COPYING)).

## Relationship with **urlwatch**

This project is a fork of [urlwatch 2.21](https://github.com/thp/urlwatch/tree/346b25914b0418342ffe2fb0529bed702fddc01f) and has since added many features; see the [comparison](https://webchanges.readthedocs.io/en/stable/_static/webchanges-vs-urlwatch.html).
