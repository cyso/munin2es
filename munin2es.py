#!/usr/bin/env python
#
# Copyright (c) 2014 Cyso < development [at] cyso . com >
#
# This file is part of munin2es.
#
# munin2es is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# munin2es is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with munin2es. If not, see <http://www.gnu.org/licenses/>.
#

import logging
from munin2es import process_munin_client
from chaos.logging import get_logger

## Initialize root logger with handlers
## All other loggers will propagate their events to the root logger, and use
## its handlers and settings.
get_logger(None, level=logging.DEBUG, handlers={"syslog": None, "console": None})

process_munin_client(node="localhost", port=4949)
