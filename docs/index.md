---
title: GUI automation bot
layout: default
---

## [](#about)About Guibot

There are a lot of mundane tasks related to GUI operations that could greatly benefit from automation. These could range from overnight web monitoring for good bike rentals to testing a software product's GUI on each release cycle. This is where a bot becomes a useful assistant and the guibot library offers a way to quickly build python scripts for this.

## [](#usage)How to use

Here is our minimal bootstrap example for those eager to start without any reading:

```python
from guibot.guibot_simple import *

initialize()
add_path('images')

if exists('all_shapes'):
    click('all_shapes')
else:
    type_text('Shapes do not exist')
```

For those interested in more serious examples, please check [Read the Docs](http://guibot.readthedocs.io/en/latest/) where you can find a gradation of them with increasing difficulty. The quick readers will also most probably need the complete API documentation which can also be found there.

## [](#download)Download

The most platform independent way to get the code is through PyPI as

```
pip install guibot
```

RPM and Debian packages are also produced from the sources provided in the packaging folder. For more information on these, check the [Packaging Wiki](https://github.com/intra2net/guibot/wiki/Packaging) page.
