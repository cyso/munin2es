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
from .. import get_cli_args_parser
from configobj import ConfigObj
from chaos.arguments import get_default_config_file

suppress = [ "help", "config", "version", "quiet" ]

argparser = get_cli_args_parser(ConfigObj())

override = {
	"daemonize": False,
	"amqphost": "127.0.0.1",
	"amqpuser": "guest",
	"amqppass": "guest",
	"pidfile": "/var/run/munin2es.pid",
	"hostdir": "/etc/munin2es-hosts.d",
}

print get_default_config_file(argparser, suppress=suppress, default_override=override)
