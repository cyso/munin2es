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

""" CLI Argument parsing related functions. """

from __future__ import absolute_import
import logging, sys
from .version import NAME
from chaos.arguments import get_config_argparse
from configobj import ConfigObj

def get_cli_args_validator():
	""" Builds a configspec ConfigObj, that can be used as validator. """
	rules = [
		"debug = boolean",
		"daemonize = boolean",
		"uid = string",
		"gid = string",
		"pidfile = string",
		"interval = integer",
		"timeout = integer",
		"requeuetimeout = integer",
		"hostdir = string",
		"workers = integer",
		"amqphost = string",
		"amqpport = integer",
		"amqpuser = string",
		"amqppass = string",
		"amqpvhost = string",
		"amqpexchange = string",
		"amqproutingkey = string",
		"amqppassive = boolean",
		"amqpexchangedurable = boolean",
		"amqpautodelete = boolean",
		"amqpmessagedurable = boolean"
	]

	return ConfigObj(rules, list_values=False)

def get_cli_args_parser(config, suppress=None):
	""" Builds an ArgumentParser to parse incoming CLI arguments. """

	if not suppress:
		suppress = []

	arg_parser = get_config_argparse(suppress=suppress)
	arg_parser.prog = NAME
	arg_parser.description = "{0} is an interface between Munin and Elasticsearch, to allow indexing Munin metrics using Elasticsearch.".format(NAME)
	arg_parser.add_argument("--debug",			action="store_true",			default=config.get("debug", False),					help="When used with verbose, also debug backend library logging messages.")
	arg_parser.add_argument("--daemonize",		action="store_true",			default=config.get("daemonize", False),				help="Daemonize the program.")
	arg_parser.add_argument("--uid",			metavar="UID",		type=str,	default=config.get("uid", None),					help="User to switch to after daemonizing.")
	arg_parser.add_argument("--gid",			metavar="GID",		type=str,	default=config.get("gid", None),					help="Group to switch to after daemonizing.")
	arg_parser.add_argument("--pidfile",		metavar="PID",		type=str,	default=config.get("pidfile", None),				help="Where to create a PID file after daemonizing.")
	arg_parser.add_argument("--interval",		metavar="INT",		type=int,	default=config.get("interval", 5*60),				help="Minimum interval between Munin fetches.")
	arg_parser.add_argument("--timeout",		metavar="TIM",		type=int,	default=config.get("timeout", 5),					help="Connection timeout in seconds.")
	arg_parser.add_argument("--fetchtimeout",	metavar="FTIM",		type=int,	default=config.get("fetchtimeout", 60),				help="Data fetch timeout in seconds.")
	arg_parser.add_argument("--requeuetimeout",		metavar="RTIM",	type=int,	default=config.get("requeuetimeout", 6*60),			help="Requeue timeout in seconds.")
	arg_parser.add_argument("--hostdir",		metavar="HDIR",		type=str,	default=config.get("hostdir", None),				help="Directory that contains host configuration files.")
	arg_parser.add_argument("--workers",		metavar="W",		type=int,	default=config.get("workers", 10),					help="How many worker processes to spawn.")
	arg_parser.add_argument("--amqphost",		metavar="AH",		type=str,	default=config.get("amqphost", None),				help="AMQP hostname.")
	arg_parser.add_argument("--amqpport",		metavar="AP",		type=int,	default=config.get("amqpport", 5672),				help="AMQP port.")
	arg_parser.add_argument("--amqpuser",		metavar="AU",		type=str,	default=config.get("amqpuser", ""),					help="AMQP username.")
	arg_parser.add_argument("--amqppass",		metavar="APW",		type=str,	default=config.get("amqppass", ""),					help="AMQP password.")
	arg_parser.add_argument("--amqpvhost",		metavar="AV",		type=str,	default=config.get("amqpvhost", "/"),				help="AMQP vhost.")
	arg_parser.add_argument("--amqpexchange",	metavar="AE",		type=str,	default=config.get("amqpexchange", "munin2es"),		help="AMQP exchange.")
	arg_parser.add_argument("--amqproutingkey",	metavar="ARK",		type=str,	default=config.get("amqproutingkey", "munin2es"),	help="AMQP routing key.")
	arg_parser.add_argument("--amqppassive",	action="store_true",			default=config.get("amqppassive", True),			help="AMQP exchange creation passivity.")
	arg_parser.add_argument("--amqpexchangedurable",	action="store_true",	default=config.get("amqpexchangedurable", False),	help="AMQP exchange durability.")
	arg_parser.add_argument("--amqpautodelete",	action="store_true",			default=config.get("amqpautodelete", False),		help="AMQP exchange auto-delete.")
	arg_parser.add_argument("--amqpmessagedurable",	action="store_true",		default=config.get("amqpmessagedurable", False),	help="AMQP message durability.")

	return arg_parser

def parse_cli_args(config):
	""" Parses incoming CLI arguments and performs basic validation. """

	args = get_cli_args_parser(config).parse_args()

	if args.hostdir == None or args.hostdir == "None":
		logging.getLogger(__name__).error("No hostdir specified, nothing to do...")
		sys.exit(0)

	return args
