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
from .elasticsearch import BulkMessage, generate_index_name, DAILY
from .amqp import Queue, NORMAL_MESSAGE, PERSISTENT_MESSAGE

NAME = "munin2es"
VERSION = "0.1"
BUILD = "AAAAA"

STARTARG = None
QUIET = None
VERBOSE = None

HOSTDIR = None
WORKERS = None

AMQPHOST = None
AMQPCREDENTIALS = None
AMQPEXCHANGE = None
AMQPROUTINGKEY = None
AMQPMESSAGEDURABLE = None

def parse_cli_args(config):
	arg_parser = get_config_argparse()
	arg_parser.description = "{0} is an interface between Munin and Elasticsearch, to allow indexing Munin metrics using Elasticsearch.".format(NAME)
	arg_parser.add_argument("--hostdir",		metavar="HDIR",		type=str,	default=config.get("hostdir", None),				help="Directory that contains host configuration files.")
	arg_parser.add_argument("--workers",		metavar="W",		type=int,	default=config.get("workers", 10),					help="How many worker processes to spawn.")
	arg_parser.add_argument("--amqphost",		metavar="AH",		type=str,	default=config.get("amqphost", None),				help="AMQP hostname.")
	arg_parser.add_argument("--amqpport",		metavar="AP",		type=int,	default=config.get("amqpport", 5672),				help="AMQP port.")
	arg_parser.add_argument("--amqpuser",		metavar="AU",		type=str,	default=config.get("amqpuser", None),				help="AMQP username.")
	arg_parser.add_argument("--amqppass",		metavar="APW",		type=str,	default=config.get("amqppass", None),				help="AMQP password. Note that this might be visible in ps output!")
	arg_parser.add_argument("--amqpvhost",		metavar="AV",		type=str,	default=config.get("amqpvhost", "/"),				help="AMQP vhost.")
	arg_parser.add_argument("--amqpexchange",	metavar="AE",		type=str,	default=config.get("amqpexchange", "munin2es"),		help="AMQP exchange.")
	arg_parser.add_argument("--amqproutingkey",	metavar="ARK",		type=str,	default=config.get("amqproutingkey", "munin2es"),	help="AMQP routing key.")
	arg_parser.add_argument("--amqppassive",	action="store_true",			default=config.get("amqppassive", False),			help="AMQP exchange creation passivity.")
	arg_parser.add_argument("--amqpexchangedurable",	action="store_true",		default=config.get("amqpexchangedurable", False),		help="AMQP exchange durability.")
	arg_parser.add_argument("--amqpautodelete",	action="store_true",			default=config.get("amqpautodelete", False),		help="AMQP exchange auto-delete.")
	arg_parser.add_argument("--amqpmessagedurable",	action="store_true",		default=config.get("amqpmessagedurable", False),	help="AMQP message durability.")
	arg_parser.add_argument("--debug",			action="store_true",			default=config.get("debug", False),					help="When used with verbose, also debug backend library logging messages.")

	args = arg_parser.parse_args()

	if args.hostdir == None:
		get_logger(__name__).error("No hostdir specified, nothing to do...")
		sys.exit(0)

	return args

def reload_config():
	global STARTARG, QUIET, VERBOSE, DEBUG
	global HOSTDIR, WORKERS
	global AMQPHOST, AMQPCREDENTIALS, AMQPEXCHANGE, AMQPROUTINGKEY, AMQPMESSAGEDURABLE

	config = get_config(STARTARG)
	args = parse_cli_args(config)

	QUIET = args.quiet
	VERBOSE = args.verbose
	DEBUG = args.debug

	HOSTDIR = args.hostdir
	WORKERS = args.workers

	AMQPHOST = (args.amqphost, args.amqpport)
	AMQPCREDENTIALS = (args.amqpuser, args.amqppass)
	AMQPEXCHANGE = {
		"exchange": args.amqpexchange,
		"exchange_type": "direct",
		"passive": args.amqppassive
	}
	if not args.amqppassive:
		AMQPEXCHANGE.update({
			"durable": args.amqpexchangedurable,
			"auto_delete": args.amqpautodelete
		})
	AMQPROUTINGKEY = args.amqproutingkey
	AMQPMESSAGEDURABLE = args.amqpmessagedurable

def process_munin_client_to_bulk(node, port=4949, address=None, index=None):
	client = MuninNodeClient(node, port, address)
	messages = client.get_all_messages(preformat=True)

	if index is None:
		index = generate_index_name("munin", DAILY)
	bulk = BulkMessage(index=index, message=messages, encode_message=False, datatype="munin")

	return bulk

def bulk_to_rabbitmq(message):
	queue = Queue(AMQPHOST, AMQPCREDENTIALS, AMQPEXCHANGE, AMQPROUTINGKEY)
	if isinstance(message, list):
		for m in message:
			queue.publish("".join(m), { "content_type": "text/plain", "delivery_mode": PERSISTENT_MESSAGE if AMQPMESSAGEDURABLE else NORMAL_MESSAGE })
	else:
			queue.publish(message, { "content_type": "text/plain", "delivery_mode": PERSISTENT_MESSAGE if AMQPMESSAGEDURABLE else NORMAL_MESSAGE })
	queue.close()

def process_munin_node(host, config):
	logger = get_logger(__name__)
	logger.info("Starting fetch run for {0}".format(host))
	address = host
	port = 4949
	if "address" in config:
		address = config['address']
	if "port" in config:
		port = config['port']
	logger.debug("- Using address: {0}, port: {1}".format(address, port))
	index = generate_index_name("munin", DAILY)
	bulk = process_munin_client_to_bulk(node=host, port=port, address=address, index=index)
	bulk_to_rabbitmq(message=bulk.generate(as_objects=True))

def hello(text):
	get_logger(__name__).info(text)
