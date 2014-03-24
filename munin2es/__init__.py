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

NAME = "munin2es"
VERSION = "0.1"
BUILD = "AAAAA"

THREADS = None
INTERVAL = None

import logging, logging.handlers, os
from chaos.threads import Threads
from chaos.scheduler import Scheduler
from chaos.logging import get_logger

def initialize():
	global THREADS, INTERVAL

	get_logger(__name__).info("Initializing...")

	if THREADS is None:
		THREADS = Threads()

	testThread = Scheduler(2, hello, "testThread", True, text="Hello")

	THREADS.registerThread("test", testThread)

	THREADS.startAll()

def signal_handler(signum=None, frame=None):
	global THREADS
	if type(signum) != type(None):
		get_logger(__name__).info("Caught signal {0}".format(signum))
		THREADS.stopAll(exit=True)

def hello(text):
	get_logger(__name__).info(text)
