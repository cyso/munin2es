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

import sys, signal, time, setproctitle

setproctitle.setproctitle("munin2es")

import logging
from argparse import ArgumentParser
import munin2es
from munin2es import process_munin_client
from chaos.arguments import get_config_arguments
from chaos.logging import get_logger

## Initialize root logger with default handlers
get_logger(None, level=logging.INFO, handlers={"syslog": None, "console": None})

(config_arg, config_unknown) = get_config_arguments()

print config_arg
print config_unknown

log_handlers = {}
if not config_arg.version and not config_arg.help:
	log_handlers['syslog'] = None
loglevel = logging.INFO
if config_arg.verbose:
	loglevel = logging.DEBUG
if not config_arg.quiet:
	log_handlers['console'] = None

## Reset the root logger with the new values
## All other loggers will propagate their events to the root logger, and use
## its handlers and settings.
get_logger(None, level=loglevel, handlers=log_handlers)

## Get the actual logger we will use
logger = get_logger(munin2es.NAME)

if config_arg.version:
	logger.info("{0} version {1} ({2})".format(munin2es.NAME, munin2es.VERSION, munin2es.BUILD))
	sys.exit(0)

if not config_arg.help:
	logger.info("{0} version {1} ({2}) starting...".format(munin2es.NAME, munin2es.VERSION, munin2es.BUILD))

munin2es.STARTARG = config_arg

munin2es.reload_config()
print munin2es.HOSTDIR
print munin2es.WORKERS

#process_munin_client(node="localhost", port=4949)
