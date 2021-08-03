# s2coastalbot

Twitter bot that posts newly acquired Sentinel-2 images of coastal areas.

Heavily inspired from sentinel2-bot.

### Installation

```bash
$ conda create -n s2coastalbot python=3
$ conda activate s2coastalbot
$ cd /path/to/s2coastalbot/where/setup.py/is
$ pip intall -e .
```

### TODO

* Add exceptions and retries for downloading
* Add logs
* Improve postprocessing
    * Improve histograms
    * Subset instead of downsampling image
* Download only full size images (and not images on edge of swath)
* Add data folder cleaning routine
