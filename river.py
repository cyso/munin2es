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

""" Helper tool for munin2es to handle Elasticsearch River configurations. """

import sys, signal, time, setproctitle

setproctitle.setproctitle("munin2es-river")

import logging
from argparse import ArgumentParser
import munin2es
from munin2es.elasticsearch import create_river_config, delete_river_config
from chaos.arguments import get_config_arguments, get_config_argparse
from chaos.logging import get_logger

## Initialize root logger with default handlers
get_logger(None, level=logging.INFO, handlers={"syslog": None, "console": None})

arg_parser = get_config_argparse(suppress=["config"])
arg_parser.description = "{0} is a small tool to edit river configuration in Elasticsearch.".format(munin2es.NAME + "-river")
arg_parser.add_argument("--settings",	metavar="S", required=False, type=str, default=None, help="File with JSON formatted River configuration.")
arg_parser.add_argument("--river", 		metavar="R", required=True,  type=str, default=None, help="Name of the River plugin to configure.")
arg_parser.add_argument("--name",		metavar="N", required=True,  type=str, default=None, help="Name of the River plugin instance.")
arg_parser.add_argument("--action",		metavar="A", required=True,  type=str, default=None, help="Action to perform: create|delete.")
arg_parser.add_argument("--host",		metavar="H", required=False, type=str, default="localhost", 
		help="What Elasticsearch host to connect to. Defaults to localhost.")
arg_parser.add_argument("--port",		metavar="P", required=False, type=int, default=9200, help="What Elasticsearch port to connect to. Defaults to 9200.")

args = arg_parser.parse_args()

## Set log handling based on initial configuration
log_handlers = {}
if not args.version:
	log_handlers['syslog'] = None
loglevel = logging.INFO
if args.verbose:
	loglevel = logging.DEBUG
if not args.quiet:
	log_handlers['console'] = None

## Reset the root logger with the new values
## All other loggers will propagate their events to the root logger, and use
## its handlers and settings.
get_logger(None, level=loglevel, handlers=log_handlers)

## The backend loggers for urllib and elasticsearch are really chatty, let's limit them if --verbose is not set
if not args.verbose:
	get_logger("urllib3.connectionpool", level=logging.ERROR)
	get_logger("elasticsearch", level=logging.ERROR)

## Get the actual logger we will use
logger = get_logger(munin2es.NAME + "-river")

if args.version:
	logger.info("{0}-river version {1} ({2})".format(munin2es.NAME, munin2es.VERSION, munin2es.BUILD))
	sys.exit(0)

logger.info("{0}-river version {1} ({2}) starting...".format(munin2es.NAME, munin2es.VERSION, munin2es.BUILD))

if not args.action in [ "create", "delete" ]:
	logger.error("ERROR: --action must be either create or delete.")
	sys.exit(1)

if args.action == "create" and not args.settings:
	logger.error("ERROR: --settings must be supplied when using --action create.")
	sys.exit(1)

settings = ""
if args.action == "create":
	try:
		f = open(args.settings, "rU")
		settings = f.read()
	except IOError, e:
		logger.error("ERROR: could not open JSON River settings file: " + str(e))
		sys.exit(1)

	if not settings:
		logger.error("ERROR: JSON River settings file was empty or unreadable.")
		sys.exit(1)

	logger.info("Performing Elasticsearch River create command")
	try:
		create_river_config(river=args.river, name=args.name, config=settings, host=args.host, port=args.port)
	except Exception, e:
		logging.error("ERROR: failed to create river config: " + str(e))
		sys.exit(1)

elif args.action == "delete":
	logger.info("Performing Elasticsearch River delete command")
	try:
		delete_river_config(river=args.river, name=args.name, host=args.host, port=args.port)
	except Exception, e:
		logging.error("ERROR: failed to delete river config: " + str(e))
		sys.exit(1)

logger.info("Done.")
