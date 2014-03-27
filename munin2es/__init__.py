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

from __future__ import absolute_import
import logging, logging.handlers, os, sys
from chaos.arguments import get_config_argparse
from chaos.config import get_config, get_config_dir
from chaos.logging import get_logger
from .muninnode import MuninNodeClient
from .elasticsearch import BulkMessage

NAME = "munin2es"
VERSION = "0.1"
BUILD = "AAAAA"

STARTARG = None

HOSTDIR = None
WORKERS = None
QUIET = None
VERBOSE = None

def parse_cli_args(config):
	arg_parser = get_config_argparse()
	arg_parser.description = "{0} is n interface between Munin and Elasticsearch, to allow indexing Munin metrics using Elasticsearch.".format(NAME)
	arg_parser.add_argument("--hostdir",	metavar="HDIR",		type=str,	default=config.get("hostdir", None),	help="Directory that contains configuration files.")
	arg_parser.add_argument("--workers",	metavar="W",		type=int,	default=config.get("workers", 10),		help="How many worker processes to spawn.")

	args = arg_parser.parse_args()

	if args.hostdir == None:
		get_logger(__name__).error("No hostdir specified, nothing to do...")
		sys.exit(0)

	return args

def reload_config():
	global STARTARG, HOSTDIR, QUIET, VERBOSE

	config = get_config(STARTARG)
	args = parse_cli_args(config)

	HOSTDIR = args.hostdir
	WORKERS = args.workers
	QUIET = args.quiet
	VERBOSE = args.verbose

def process_munin_client(node, port=4949):
	client = MuninNodeClient(node, port)
	messages = client.get_all_messages(preformat=True)

	bulk = BulkMessage(index="munin-2014.03.25", message=messages, encode_message=False, datatype="munin")

	print bulk.generate()

def hello(text):
	get_logger(__name__).info(text)
