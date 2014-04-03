#!/usr/bin/env python
# Copyright (c) 2014 Nick Douma < n.douma [at] nekoconeko . nl >
#
# This file is part of chaos, a.k.a. python-chaos .
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3.0 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library. If not, see 
# <http://www.gnu.org/licenses/>.

from munin2es.version import NAME as PNAME, VERSION as PVERSION
from distutils.core import setup
import linecache

NAME = PNAME
VERSION = PVERSION
DESCRIPTION = linecache.getline("README.md", 4)

setup(
	name=NAME,
	version=VERSION,
	description=DESCRIPTION,
	license="GPL3",
	author="Nick Douma",
	author_email="n.douma@nekoconeko.nl",
	url="https://github.com/Cysource/munin2es",
	packages=["munin2es"],
	scripts=["main.py", "river.py"],
	data_files=[
		("/etc", ["doc/munin2es.config"]),
		("/etc/init.d", ["doc/{0}".format(NAME)]),
		("/usr/share/doc/{0}".format(NAME), ["doc/river_example.json"])
	]
)
