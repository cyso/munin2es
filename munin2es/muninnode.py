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

import json
import socket
import datetime
from dateutil.tz import tzlocal

class MuninNodeClient(object):
	""" Connects to Munin Node, and provides easy access to its data. """

	def __init__(self, hostname, port=4949, address=None):
		""" Connect to the given host and port. """
		self.connection = socket.create_connection((hostname if not address else address, port))
		self.file = self.connection.makefile()
		self.hello = self._readline()
		self.hostname = hostname

	def _readline(self):
		return self.file.readline().strip()

	def _iterline(self):
		while True:
			line = self._readline()
			if not line:
				break
			elif line.startswith('#'):
				continue
			elif line == '.':
				break
			yield line

	def list(self):
		""" List all available Munin Node modules. """
		self.connection.sendall("list\n")
		return self._readline().split(' ')

	def fetch(self, key):
		""" Fetch the counters for the given Munin Node module. """
		self.connection.sendall("fetch %s\n" % key)
		ret = {}
		data = ret # For non-multigraph, we make a single-level dictionary
		for line in self._iterline():
			if line.startswith("multigraph "):
				subkey = line.split()[1]
				ret[subkey] = {}  # use nested dictionaries for multigraph
				data = ret[subkey]
				continue
			key, rest = line.split('.', 1)
			prop, value = rest.split(' ', 1)
			if value == 'U':
				value = None
			else:
				value = float(value)
			data[key] = value
		return ret

	def config(self, key, mangle=False):
		""" Fetch the configuration for the given Munin Node module. """
		self.connection.sendall("config %s\n" % key)
		ret = {}
		for line in self._iterline():
			if line.startswith('graph_'):
				key, value = line.split(' ', 1)
				ret[key] = value
			else:
				key, rest = line.split('.', 1)
				prop, value = rest.split(' ', 1)
				if not ret.get(key):
					ret[key] = {}
				ret[key][prop] = value
		if mangle:
			return self._mangle_config(ret)
		else:
			return ret

	def _mangle_config(self, config):
		""" Mangle the configuration data, and format it differently. """
		output = { "graph": { }, "specific": { } }
		for key, value in config.iteritems():
			if key.startswith("graph_"):
				output["graph"][key.replace("graph_", "", 1)] = value
			elif isinstance(value, dict):
				output["specific"][key] = value
		return output

	def get_all_messages(self, preformat=True, **kwargs):
		""" Retrieve all module values as MuninMessage. If preformat is True, kwargs is passed to MuninMessage.format()"""
		modules = self.list()
		messages = []

		for module in modules:
			message = MuninMessage(hostname=self.hostname, module=module, config=self.config(module, mangle=True), values=self.fetch(module))
			if preformat:
				message = message.format(**kwargs)
			messages.extend(message)

		return messages

	def nodes(self):
		""" List the nodes Munin Node can access. """
		self.connection.sendall("nodes\n")
		return [ line for line in self._iterline() ]

	def version(self):
		""" Fetch the version of Munin Node. """
		self.connection.sendall("version\n")
		return self._readline()

class MuninMessage(object):
	""" Format Munin Node output into (JSON) messages. """

	def __init__(self, hostname, module, config={}, values={}, timestamp=True):
		""" Initialize a new MuninMessage for the given configuration and values. """
		self.hostname = hostname
		self.module = module
		self.config = config
		self.values = values
		self.timestamp = None
		if timestamp:
			self.timestamp = datetime.datetime.now(tzlocal()).isoformat()

	def format(self, as_string=True, individual=True):
		"""
		Format the given configuration and values into JSON strings.
		If as_string is True: output will be a JSON string of a list of messages.
		If individual is also True: output will be a list of JSON strings, each a single message.
		If neither are True: output will be a list of Python objects.
		"""
		messages = []
		for key, value in self.values.iteritems():
			message = {
				"graph": self.config["graph"],
				"config": self.config["specific"][key],
				"hostname": self.hostname,
				"module": self.module,
				"key": key,
				"value": value
			}
			if self.timestamp:
				message['timestamp'] = self.timestamp
			if as_string and individual:
				messages.append(json.dumps(message))
		if as_string and individual:
			return messages
		elif as_string:
			return json.dumps(messages)
		else:
			return messages
