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

""" Main executable for munin2es. """

import sys, signal, setproctitle, logging, daemon
import munin2es

setproctitle.setproctitle(munin2es.NAME)

from lockfile import LockError, LockFailed
from munin2es import dispatcher
from chaos.arguments import get_config_arguments
from chaos.logging import get_logger
from daemon.pidlockfile import TimeoutPIDLockFile

def get_log_handlers(config):
	""" Create a log handlers map based on the passed configuration. """
	log_handlers = {}
	if not config.version and not config.help:
		log_handlers['syslog'] = None
	loglevel = logging.INFO
	if config.verbose:
		loglevel = logging.DEBUG
	if not config.quiet:
		log_handlers['console'] = None

	return (loglevel, log_handlers)

def initialize(name, version, build):
	""" Setup the environment. """
	## Initialize root logger with default handlers
	get_logger(None, level=logging.INFO, handlers={"syslog": None, "console": None})

	config_arg = get_config_arguments()[0]

	loglevel, log_handlers = get_log_handlers(config_arg)

	## Reset the root logger with the new values
	## All other loggers will propagate their events to the root logger, and use
	## its handlers and settings.
	get_logger(None, level=loglevel, handlers=log_handlers)

	## Get the actual logger we will use
	logger = get_logger(name)

	if config_arg.version:
		logger.info("{0} version {1} ({2})".format(name, version, build))
		sys.exit(0)

	munin2es.STARTARG = config_arg
	munin2es.reload_config()

	## The backend loggers for urllib, elasticsearch and pika are really chatty, let's limit them unless --verbose and --debug are both set
	if not (munin2es.VERBOSE and munin2es.DEBUG):
		get_logger("urllib3.connectionpool", level=logging.ERROR)
		get_logger("elasticsearch", level=logging.ERROR)
		get_logger("pika.adapters.base_connection", level=logging.ERROR)
		get_logger("pika", level=logging.WARNING)

	if not config_arg.help:
		logger.info("{0} version {1} ({2}) starting...".format(name, version, build))


def main():
	""" Main entrypoint after environment has been initialized. """
	logger = get_logger(munin2es.NAME)

	if munin2es.DAEMONIZE:
		logger.info("Daemonizing...")

		pidfile = None
		if munin2es.PIDFILE:
			pidfile = TimeoutPIDLockFile(munin2es.PIDFILE, acquire_timeout=5)

		context = daemon.DaemonContext(uid=munin2es.UID, gid=munin2es.GID, pidfile=pidfile)
		context.signal_map = {
			signal.SIGINT: munin2es.kill_handler,
			signal.SIGTERM: munin2es.kill_handler,
			signal.SIGUSR1: munin2es.config_handler,
			signal.SIGHUP: munin2es.config_handler
		}

		loglevel, log_handlers = get_log_handlers(munin2es.STARTARG)

		if "console" in log_handlers.keys():
			logger.info("Disabling output to console")
			del(log_handlers["console"])
			get_logger(None, level=loglevel, handlers=log_handlers)

		try:
			with context:
				dispatcher()
		except LockFailed, lfe:
			logger.fatal("Failed to create PID file! " + str(lfe))
		except LockError, lee:
			logger.fatal("Failed to acquire lock for PID file! " + str(lee))

	else:
		## Register signal handlers
		signal.signal(signal.SIGINT, munin2es.kill_handler)
		signal.signal(signal.SIGTERM, munin2es.kill_handler)
		signal.signal(signal.SIGUSR1, munin2es.config_handler)
		signal.signal(signal.SIGHUP, munin2es.config_handler)

		dispatcher()
	logger.info("All done!")

if __name__ == "__main__":
	initialize(name=munin2es.NAME, version=munin2es.VERSION, build=munin2es.BUILD)
	main()
