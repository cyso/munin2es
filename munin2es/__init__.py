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
import logging, logging.handlers, os, sys, datetime, time, setproctitle
from multiprocessing import Process, Manager
from Queue import Empty
from chaos.arguments import get_config_argparse
from chaos.config import get_config, get_config_dir
from chaos.logging import get_logger
from chaos.multiprocessing.workers import Workers
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
INTERVAL = None

AMQPHOST = None
AMQPCREDENTIALS = None
AMQPEXCHANGE = None
AMQPROUTINGKEY = None
AMQPMESSAGEDURABLE = None

QUEUELIMITFACTOR = 3
RELOADCONFIG = False
STOP = False

def parse_cli_args(config):
	arg_parser = get_config_argparse()
	arg_parser.description = "{0} is an interface between Munin and Elasticsearch, to allow indexing Munin metrics using Elasticsearch.".format(NAME)
	arg_parser.add_argument("--interval",		metavar="INT",		type=int,	default=config.get("interval", 5*60),				help="Minimum interval between Munin fetches.")
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
	global HOSTDIR, WORKERS, INTERVAL
	global AMQPHOST, AMQPCREDENTIALS, AMQPEXCHANGE, AMQPROUTINGKEY, AMQPMESSAGEDURABLE

	config = get_config(STARTARG)
	args = parse_cli_args(config)

	QUIET = args.quiet
	VERBOSE = args.verbose
	DEBUG = args.debug

	HOSTDIR = args.hostdir
	WORKERS = args.workers
	INTERVAL = args.interval

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

def dispatcher():
	""" Main worker, responsible for mainting Queues and distributing work. """
	global RELOADCONFIG, STOP

	manager = Manager()
	munin_queue = manager.Queue()
	message_queue = manager.Queue()
	done_queue = manager.Queue()
	workers = Workers()

	logger = get_logger(__name__ + ".dispatcher")
	logger.info("Dispatcher starting...")

	for i in range(WORKERS):
		name = "munin-{0}".format(str(i))
		p = Process(name=name, target=munin_worker, args=(name, munin_queue, done_queue))
		workers.registerWorker(name, p)

	for i in range(1):
		name = "message-{0}".format(str(i))
		p = Process(name=name, target=message_worker, args=(name, message_queue, done_queue))
		workers.registerWorker(name, p)

	#for i in range(1):
	#	name = "test-{0}".format(str(i))
	#	p = Process(name=name, target=test_worker, args=(name, message_queue, done_queue))
	#	workers.registerWorker(name, p)

	RELOADCONFIG = True
	timestamps = {}
	workers.startAll()

	logger.info("Starting main loop")
	lastrun = datetime.datetime.now()

	while (not STOP):
		if RELOADCONFIG:
			logger.info("Reloading host config")
			hosts = get_config_dir(HOSTDIR)
			RELOADCONFIG = False

		now = datetime.datetime.now()
		logger.debug("Checking timestamps against {0}".format(str(now)))

		if munin_queue.qsize() < (len(hosts) * QUEUELIMITFACTOR):
			for (host, config) in hosts.iteritems():
				if not host in timestamps.keys():
					timestamps[host] = (now, True)
				elif (now - timestamps[host][0]).total_seconds() > INTERVAL and timestamps[host][1]:
					munin_queue.put((host, config))
					timestamps[host] = (now, False)
					logger.debug("Queued munin work for {0}".format(host))
				elif (now - timestamps[host][0]).total_seconds() > (INTERVAL * 4) and not timestamps[host][1]:
					munin_queue.put((host, config))
					timestamps[host] = (now, False)
					logger.warning("No response received for host {0}, requeued".format(host))
		else:
			logger.warning("Munin worker queue is full, will not queue more work.")

		while True:
			try:
				item = done_queue.get(block=False)
			except Empty, e:
				logger.debug("Done queue was empty.")
				break

			if item[0] == "error":
				# Do error stuff
				pass
			elif item[0] == "munin":
				message_queue.put((item[1], item[2]))
				logger.debug("Dispatched message for host {0}".format(item[1]))
			elif item[0] == "message":
				timestamps[item[1]] = (timestamps[item[1]][0], True)
				logger.debug("Marked {0} as successful".format(item[1]))
			else:
				logger.error("Received a done message with unknown type: {0}".format(item[0]))

		if (lastrun - now).total_seconds() < 5:
			time.sleep(5)
		lastrun = datetime.datetime.now()

	logger.info("Loop exited, cleaning up...")
	## Empty queues and fill with STOP messages
	try:
		while not munin_queue.empty():
			munin_queue.get(block=False)
	except Empty, e:
		# We're cleaning up, no need to handle this error
		pass

	try:
		while not message_queue.empty():
			message_queue.get(block=False)
	except Empty, e:
		# We're cleaning up, no need to handle this error
		pass

	logger.info("Passing STOP messages to workers")
	for i in range(WORKERS):
		munin_queue.put("STOP")
	for i in range(1):
		message_queue.put("STOP")

	workers.stopAll()

def munin_worker(name, work, response):
	""" Work thread, handles connections to Munin and fetching of details. """
	logger = get_logger("{0}.{1}.{2}".format(__name__, "munin_worker", name))
	setproctitle.setproctitle("munin2es " + name)
	while True:
		try:
			item = work.get(block=True, timeout=5)
		except Empty, e:
			# No work is no cause for panic, dear.
			continue

		logger.debug(item)
		if item == "STOP":
			break
		host, config = item

		logger.info("Fetching Munin info from {0}".format(host))
		address = host
		port = 4949
		if "address" in config:
			address = config['address']
		if "port" in config:
			port = config['port']

		logger.debug("- Using address: {0}, port: {1}".format(address, port))
		index = generate_index_name("munin", DAILY)
		bulk = process_munin_client_to_bulk(node=host, port=port, address=address, index=index)

		response.put(("munin", host, bulk.generate(as_objects=True)))
	logger.debug("Exiting loop")

def message_worker(name, work, response):
	""" Message thread, handles sending Munin information to AMQP. """
	logger = get_logger("{0}.{1}.{2}".format(__name__, "message_worker", name))
	setproctitle.setproctitle("munin2es " + name)
	logger.info("Opening AMQP connection to {0}".format(AMQPHOST))
	queue = Queue(AMQPHOST, AMQPCREDENTIALS, AMQPEXCHANGE, AMQPROUTINGKEY)

	while True:
		try:
			item = work.get(block=True, timeout=5)
		except Empty, e:
			# No work is no cause for panic, dear.
			continue

		if item == "STOP":
			break
		host, message = item

		logger.info("Sending AMQP message for host {0}".format(host))

		if isinstance(message, list):
			for m in message:
				queue.publish("".join(m), { "content_type": "text/plain", "delivery_mode": PERSISTENT_MESSAGE if AMQPMESSAGEDURABLE else NORMAL_MESSAGE })
		else:
			queue.publish(message, { "content_type": "text/plain", "delivery_mode": PERSISTENT_MESSAGE if AMQPMESSAGEDURABLE else NORMAL_MESSAGE })

		response.put(("message", host))

	logger.info("Closing AMQP connection")
	queue.close()
	logger.debug("Done")

def test_worker(name, work, response):
	""" Testing thread. """
	logger = get_logger("{0}.{1}.{2}".format(__name__, "test_worker", name))
	setproctitle.setproctitle("munin2es " + name)
	while (True):
		try:
			item = work.get(block=True, timeout=5)
		except Empty, e:
			# No work is no cause for panic, dear.
			continue

		item = str(item)
		item = (item[:75] + '..') if len(item) > 75 else item
		logger.debug(item)
		if item == "STOP":
			break
	logger.debug("Exiting loop")

def kill_handler(signum=None, frame=None):
	global STOP
	if type(signum) != type(None):
		logging.getLogger(__name__).info("Caught signal {0}".format(signum))
		STOP = True

def config_handler(signum=None, frame=None):
	global RELOADCONFIG
	if type(signum) != type(None):
		logging.getLogger(__name__).info("Caught signal {0}".format(signum))
		RELOADCONFIG = True

def hello(text):
	get_logger(__name__).info(text)
