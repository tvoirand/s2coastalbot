# s2coastalbot

[S2coastalbot](https://twitter.com/s2coastalbot) is a twitter bot that posts Sentinel-2 images acquired recently over coastal areas.

Inspired from [Sentinel2Bot](https://twitter.com/Sentinel2Bot) and [LandsatBot](https://twitter.com/LandsatBot).

Described in more details on [thibautvoirand.com/s2coastalbot](https://thibautvoirand.com/s2coastalbot/).

### Installation

```bash
$ conda create -n s2coastalbot python=3
$ conda activate s2coastalbot
$ cd /path/to/s2coastalbot/where/setup.py/is
$ pip intall -e .
```

### TODO

* [ ] Improve list of coastal tiles by using coastline vector file more precise than the [Natural Earth file](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-coastline/)
* [ ] Add specific tweet for when no image satisfying selection criteria (AOI, time range, cloud cover) was found
* [ ] Use atmospheric correction algorithm specific to the coastal environment instead of level 2 TCI image

### Contribute

Please feel free to contribute by opening issues or pull-requests!
