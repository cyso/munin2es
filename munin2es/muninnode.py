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

import socket

class MuninNodeClient(object):
	""" Connects to Munin Node, and provides easy access to its data. """

	def __init__(self, host, port=4949):
		""" Connect to the given host and port. """
		self.connection = socket.create_connection((host, port))
		self.file = self.connection.makefile()
		self.hello = self._readline()

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

	def nodes(self):
		""" List the nodes Munin Node can access. """
		self.connection.sendall("nodes\n")
		return [ line for line in self._iterline() ]

	def version(self):
		""" Fetch the version of Munin Node. """
		self.connection.sendall("version\n")
		return self._readline()
