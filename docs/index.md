---
title: GUI automation bot
layout: default
---

## [](#about)About Guibot

There are a lot of mundane tasks related to GUI operations that could greatly benefit from automation. These could range from overnight web monitoring for good bike rentals to testing a software product's GUI on each release cycle. This is where a bot becomes a useful assistant and the guibot library offers a way to quickly build python scripts for this.

## [](#usage)How to use

A simple use case scenario is the following

```python
from guibot.guibot_simple import *

initialize()
add_path('images')

if exists('all_shapes'):
    click('all_shapes')
else:
    type_text('Shapes do not exist')
```

## [](#apidoc)API reference

The full guibot library API is documented using sphinx and available on [Read the Docs](http://guibot.readthedocs.io/en/latest/).

## [](#wiki)Wiki and tutorials

Some tutorials regarding specialized topics are available on the Guibot GitHub Wiki page. The example code within the repository is good enough for more basic usage but more tutorials will be added to the wiki in the future.

## [](#download)Download

The fastest way to get the code is to through PyPI as

```
pip install guibot
```

RPM and Debian packages can also be produced from the SPEC file provided in the packaging folder. For more information, check the README or packaging page.
