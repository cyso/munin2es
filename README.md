munin2es
--------

An interface between Munin and Elasticsearch, to allow indexing Munin metrics using Elasticsearch.

Dependencies
============

* python >= 2.7
* [python-chaos]
* python-configobj
* python-daemon
* python-dateutil
* [python-elasticsearch]
* python-pika
* python-setproctitle

Building
========

No building is required to use munin2es. To build a Debian package, perform the following steps:

1. `apt-get install ubuntu-dev-tools debhelper dh-exec`

From here you can either build the package with pbuilder-dist:

2. `make -f debian/Makefile pbuild_create`
3. `make -f debian/Makefile pbuild_update`
4. `make -f debian/Makefile source_no_sign`
5. `make -f debian/Makefile pbuild CHANGES=../munin2es_xxxx_.dsc`
6. look for the resulting .deb in ~/pbuilder/saucy_result

Or directly using dpkg-buildpackage

2. `make -f debian/Makefile package`


Installing
==========

Either use the methods described above to build your own package, or install it from my PPA.

1. `add-apt-repository ppa:lordgaav/munin2es`
2. `apt-get update && apt-get install munin2es`

Using
=====


Man page
========
```
```

[python-chaos]: https://github.com/LordGaav/python-chaos
[python-elasticsearch]: https://github.com/LordGaav/python-elasticsearch
