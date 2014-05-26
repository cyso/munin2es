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

""" munin-node related classes and functions. """

import logging
import json
import socket
import datetime
from dateutil.tz import tzlocal

def mangle_config(config):
	""" Mangle configuration data, and format it differently. """
	output = { "graph": { }, "specific": { } }
	for key, value in config.iteritems():
		if key.startswith("graph_"):
			output["graph"][key.replace("graph_", "", 1)] = value
		elif isinstance(value, dict):
			output["specific"][key] = value
	return output

class MuninNodeClient(object):
	""" Connects to Munin Node, and provides easy access to its data. """

	def __init__(self, hostname, port=4949, address=None, connect_timeout=5, fetch_timeout=60):
		""" Connect to the given host and port. """
		self.connection = socket.create_connection(address=(hostname if not address else address, port), timeout=connect_timeout)
		## Python specs say that makefile() cannot be used when a timeout is set. I find no noticable difference,
		## so a timeout is still set at this point.
		self.connection.settimeout(fetch_timeout)
		self.file = self.connection.makefile()
		self.hello = self._readline()
		self.hostname = hostname
		self.logger = logging.getLogger(__name__)

		if not self.hello:
			raise IOError(0, "No hello received")

	def _readline(self):
		""" Reads one line from the internal connection. """
		return self.file.readline().strip()

	def _iterline(self):
		""" Iterates over the internal connection. """
		while True:
			line = self._readline()
			if not line:
				break
			elif line.startswith('#'):
				continue
			elif line == '.':
				break
			yield line

	def _read_to_end(self):
		""" Read from internal connection until message is finished. """
		for line in self._iterline():
			pass

	def list(self):
		""" List all available Munin Node modules. """
		self.connection.sendall("list\n")
		modules = self._readline().split(' ')
		self.logger.debug("Node {0} supports modules: {1}".format(self.hostname, " ".join(modules)))
		return modules

	def fetch(self, module):
		""" Fetch the counters for the given Munin Node module. """
		self.connection.sendall("fetch %s\n" % module)
		ret = {}
		data = ret # For non-multigraph, we make a single-level dictionary
		for line in self._iterline():
			if line.startswith("multigraph "):
				subkey = line.split()[1]
				ret[subkey] = {}  # use nested dictionaries for multigraph
				data = ret[subkey]
				continue
			try:
				key, rest = line.split('.', 1)
				prop, value = rest.split(' ', 1)
			except ValueError, vee:
				self._read_to_end()
				raise ValueError("Node {0} module {1} provided invalid data (split error), ignoring...".format(self.hostname, module))

			if value == 'U':
				value = None
			else:
				try:
					value = float(value)
				except ValueError, tee:
					self._read_to_end()
					raise ValueError("Node {0} module {1} provided invalid data (float error), ignoring...".format(self.hostname, module))
			data[key] = value
		return ret

	def config(self, module, mangle=False):
		""" Fetch the configuration for the given Munin Node module. """
		self.connection.sendall("config %s\n" % module)
		ret = {}
		for line in self._iterline():
			try:
				if line.startswith('graph_'):
					key, value = line.split(' ', 1)
					ret[key] = value
				else:
					key, rest = line.split('.', 1)
					prop, value = rest.split(' ', 1)
					if not ret.get(key):
						ret[key] = {}
					ret[key][prop] = value
			except ValueError, vee:
				self._read_to_end()
				raise ValueError("Node {0} module {1} provided invalid configuration data (split error), ignoring...".format(self.hostname, module))
		if mangle:
			return mangle_config(ret)
		else:
			return ret

	def get_all_messages(self, preformat=True, **kwargs):
		""" Retrieve all module values as MuninMessage. If preformat is True, kwargs is passed to MuninMessage.format()"""
		modules = self.list()
		messages = []

		for module in modules:
			try:
				message = MuninMessage(hostname=self.hostname, module=module, config=self.config(module, mangle=True), values=self.fetch(module))
			except ValueError, tee:
				self.logger.warning(str(tee))
				continue
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

	def __init__(self, hostname, module, config=None, values=None, timestamp=True):
		""" Initialize a new MuninMessage for the given configuration and values. """
		if config is None:
			config = {}
		if values is None:
			values = {}

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
			try:
				message = {
					"graph": self.config["graph"],
					"config": self.config["specific"][key],
					"hostname": self.hostname,
					"module": self.module,
					"key": key,
					"value": value
				}
			except KeyError:
				logging.getLogger(__name__).warning("Host {0} reported values for {1}, but did not have any configuration. Skipping value...".format(self.hostname, key))
				continue

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
