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
import logging, logging.handlers, os, sys, datetime, time, setproctitle, pwd, grp, socket
from multiprocessing import Process, Manager
from Queue import Empty
from chaos.arguments import get_config_argparse
from chaos.config import get_config, get_config_dir
from chaos.logging import get_logger
from chaos.multiprocessing.workers import Workers
from .arguments import get_cli_args_validator, get_cli_args_parser, parse_cli_args
from .muninnode import MuninNodeClient
from .elasticsearch import BulkMessage, generate_index_name, DAILY
from .amqp import Queue, NORMAL_MESSAGE, PERSISTENT_MESSAGE
from pika.exceptions import ChannelClosed, AMQPError

from .version import NAME, VERSION, BUILD

STARTARG = None
QUIET = None
VERBOSE = None
DEBUG = None

DAEMONIZE = None
UID = None
GID = None
PIDFILE = None

HOSTDIR = None
WORKERS = None
INTERVAL = None
TIMEOUT = None
REQUEUETIMEOUT = None

AMQPHOST = None
AMQPCREDENTIALS = None
AMQPEXCHANGE = None
AMQPROUTINGKEY = None
AMQPMESSAGEDURABLE = None

QUEUELIMITFACTOR = 3
RELOADCONFIG = False
STOP = False

def reload_config():
	""" (Re-)read config and cli arguments, and set them internally. """
	global QUIET, VERBOSE, DEBUG
	global DAEMONIZE, UID, GID, PIDFILE
	global HOSTDIR, WORKERS, INTERVAL, TIMEOUT, REQUEUETIMEOUT
	global AMQPHOST, AMQPCREDENTIALS, AMQPEXCHANGE, AMQPROUTINGKEY, AMQPMESSAGEDURABLE

	config = get_config(config_base=NAME, custom_file=STARTARG.config, configspec=get_cli_args_validator())
	args = parse_cli_args(config)

	QUIET = args.quiet
	VERBOSE = args.verbose
	DEBUG = args.debug

	uid = args.uid
	gid = args.gid
	pidfile = args.pidfile

	try:
		if uid == "None":
			uid = None
		elif isinstance(uid, basestring):
			uid = pwd.getpwnam(uid).pw_uid
		if gid == "None":
			gid = None
		elif isinstance(gid, basestring):
			gid = grp.getgrnam(gid).gr_gid
	except KeyError:
		get_logger("{0}.{1}".format(__name__, "reload_config")).fatal("Could not find given uid or gid.")
		sys.exit(1)

	if pidfile == "None":
		pidfile = None

	DAEMONIZE = args.daemonize
	UID = uid
	GID = gid
	PIDFILE = args.pidfile

	HOSTDIR = args.hostdir
	WORKERS = args.workers
	INTERVAL = args.interval
	TIMEOUT = args.timeout
	REQUEUETIMEOUT = args.requeuetimeout

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
	""" Convenience methode to call MuninNodeClient and process its output into a BulkMessage. """
	client = MuninNodeClient(node, port, address, TIMEOUT)
	messages = client.get_all_messages(preformat=True)

	if not messages:
		return None

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
		process = Process(name=name, target=munin_worker, args=(name, munin_queue, done_queue))
		workers.registerWorker(name, process)

	for i in range(2):
		name = "message-{0}".format(str(i))
		process = Process(name=name, target=message_worker, args=(name, message_queue, done_queue))
		workers.registerWorker(name, process)

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

		if len(hosts) == 0:
			logger.fatal("List of hosts is empty, exiting main loop")
			break

		now = datetime.datetime.now()

		work_queue_size = munin_queue.qsize()
		message_queue_size = message_queue.qsize()
		queue_limit = len(hosts) * QUEUELIMITFACTOR

		if work_queue_size < queue_limit and message_queue_size < queue_limit:
			for (host, config) in hosts.iteritems():
				if not host in timestamps.keys():
					timestamps[host] = (datetime.datetime.min, True)
					continue

				lastsecs = (now - timestamps[host][0]).total_seconds()
				lastsuccess = timestamps[host][1]
				if lastsecs > INTERVAL and lastsuccess:
					munin_queue.put((host, config))
					timestamps[host] = (now, False)
					logger.debug("Queued munin work for {0}".format(host))
				elif lastsecs > REQUEUETIMEOUT and not lastsuccess:
					munin_queue.put((host, config))
					timestamps[host] = (now, False)
					logger.warning("No response received for host {0}, requeued".format(host))
		else:
			if work_queue_size >= queue_limit:
				logger.warning("Munin worker queue is full, will not queue more work.")
			if message_queue_size >= queue_limit:
				logger.warning("AMQP message queue is full, will not queue more work.")

		while True:
			try:
				item = done_queue.get(block=False)
			except Empty:
				break

			if item[0] == "error":
				if item[2] == "FATAL":
					logger.fatal("Received fatal error from worker, stop all the things!")
					STOP = True
					continue
				logger.error("Received error for host {0}: {1}".format(item[1], item[2]))
			elif item[0] == "munin":
				message_queue.put((item[1], item[2]))
				logger.debug("Dispatched message for host {0}".format(item[1]))
			elif item[0] == "message":
				timestamps[item[1]] = (timestamps[item[1]][0], True)
				logger.debug("Marked {0} as successful".format(item[1]))
			else:
				logger.error("Received a done message with unknown type: {0}".format(item[0]))

		if (lastrun - now).total_seconds() < 1:
			time.sleep(1)
		lastrun = datetime.datetime.now()

	logger.info("Loop exited, cleaning up...")
	## Empty queues and fill with STOP messages
	try:
		while not munin_queue.empty():
			munin_queue.get(block=False)
	except Empty:
		# We're cleaning up, no need to handle this error
		pass

	try:
		while not message_queue.empty():
			message_queue.get(block=False)
	except Empty:
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
	while True:
		setproctitle.setproctitle("munin2es {0}".format(name))
		try:
			item = work.get(block=True, timeout=1)
		except Empty:
			# No work is no cause for panic, dear.
			continue

		if item == "STOP":
			break
		host, config = item

		setproctitle.setproctitle("munin2es {0} {1}".format(name, host))
		logger.info("Fetching Munin info from {0}".format(host))
		address = host
		port = 4949
		if "address" in config:
			address = config['address']
		if "port" in config:
			port = config['port']

		logger.debug("- Using address: {0}, port: {1}".format(address, port))
		index = generate_index_name("munin", DAILY)
		try:
			bulk = process_munin_client_to_bulk(node=host, port=port, address=address, index=index)
		except socket.timeout:
			response.put(("error", host, "Connection timed out"))
			continue
		except IOError, ioe:
			response.put(("error", host, ioe.strerror))
			continue

		if not bulk:
			response.put(("error", host, "No response from Munin node."))
		else:
			try:
				response.put(("munin", host, bulk.generate(as_objects=True)))
			except TypeError, tee:
				response.put(("error", host, str(tee)))
				continue
	logger.debug("Exiting loop")

def message_worker(name, work, response):
	""" Message thread, handles sending Munin information to AMQP. """
	logger = get_logger("{0}.{1}.{2}".format(__name__, "message_worker", name))
	setproctitle.setproctitle("munin2es " + name)

	queue = None
	initial = True
	stop = False
	tries = 5

	message_metadata = {
		"content_type": "text/plain",
		"delivery_mode": PERSISTENT_MESSAGE if AMQPMESSAGEDURABLE else NORMAL_MESSAGE
	}

	while not stop:
		## First nested while is for trying to reconnect to AMQP
		try:
			logger.info("Opening AMQP connection to {0}".format(AMQPHOST))
			queue = Queue(AMQPHOST, AMQPCREDENTIALS, AMQPEXCHANGE, AMQPROUTINGKEY)
		except RuntimeError, rte:
			logger.fatal("Received RuntimeError from backend, cannot continue! " + str(rte))
			response.put(("error", None, "FATAL"))
			stop = True
			continue
		except AMQPError, amqpe:
			if initial or tries == 0:
				logger.fatal("Failed to connect AMQP, cannot continue! " + str(amqpe))
				response.put(("error", None, "FATAL"))
				stop = True
				continue
			else:
				logger.error("Failed to connect to AMQP, retrying {0} times with 30 second delays. {1}".format(tries, str(amqpe)))
				tries = tries - 1
				time.sleep(30)
				continue
		except Exception, eee:
			logger.fatal("Received an unspecific error from AMQP, cannot continue! " + str(eee))
			response.put(("error", None, "FATAL"))
			stop = True
			continue

		## If we reached here, we have had at least on successful connection and have (re)connected
		## Reset counters
		initial = False
		tries = 5

		while not stop:
			## Second nested loop is the main work loop
			## We only break out if we encounter an Exception
			try:
				item = work.get(block=True, timeout=1)
			except Empty:
				# No work is no cause for panic, dear.
				continue

			if item == "STOP":
				stop = True
				continue
			host, message = item

			logger.info("Sending AMQP message for host {0}".format(host))

			try:
				if isinstance(message, list):
					for item in message:
						queue.publish("".join(item), message_metadata)
				else:
					queue.publish(message, message_metadata)
			except Exception, eee:
				## Pika specs are unclear what Exceptions to expect here
				logger.error("Received an exception from AMQP, closing connection and reconnecting. " + str(eee))
				response.put(("error", host, "AMQP exception on publish"))

				try:
					queue.close(reply_text="Disconnecting on AMQP exception")
					queue = None
				except ChannelClosed:
					## Already closed, do nothing
					pass
				break

			response.put(("message", host))

	logger.info("Closing AMQP connection")
	if queue:
		queue.close()
	logger.debug("Done")

def test_worker(name, work, response):
	""" Testing thread. """
	logger = get_logger("{0}.{1}.{2}".format(__name__, "test_worker", name))
	setproctitle.setproctitle("munin2es " + name)
	while (True):
		try:
			item = work.get(block=True, timeout=1)
		except Empty:
			# No work is no cause for panic, dear.
			continue

		item = str(item)
		item = (item[:75] + '..') if len(item) > 75 else item
		logger.debug(item)
		if item == "STOP":
			break
	logger.debug("Exiting loop")

def kill_handler(signum=None, frame=None):
	""" Handle kill-type signals, by telling the dispatcher to stop all workers. """
	global STOP
	if type(signum) != type(None):
		logging.getLogger(__name__).info("Caught signal {0}".format(signum))
		STOP = True

def config_handler(signum=None, frame=None):
	""" Handle reload-type signals, by reloading the host configuration. """
	global RELOADCONFIG
	if type(signum) != type(None):
		logging.getLogger(__name__).info("Caught signal {0}".format(signum))
		RELOADCONFIG = True

def hello(text):
	""" Test method. """
	get_logger(__name__).info(text)
