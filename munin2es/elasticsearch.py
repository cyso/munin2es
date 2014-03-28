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
import json, datetime
from dateutil.tz import tzlocal
from elasticsearch import Elasticsearch

NONE="none"
HOURLY="hour"
DAILY="day"
WEEKLY="week"
MONTHLY="month"
YEARLY="year"

INDEX_ACTION = "index"
CREATE_ACTION = "create"
DELETE_ACTION = "delete"
UPDATE_ACTION = "update"

def generate_index_name(basename, timestamping="DAY"):
	"""
	Generate the index name based on a base name and timestamping type, and the current time.

	This is basically an easy way to go from a "daily index named 'munin'" to
	munin-YYYY.MM.DD.

	Arguments
	---------
	basename: string
		Base name of the index, used for the first part of the name.
	timestamping: string
		Type of timestamping of the index name, supported values are:
		- none
		- hour   (YYYY.MM.DD.HH)
		- day    (YYYY.MM.DD)
		- week   (YYYY.WW)
		- month  (YYYY.MM)
		- yearly (YYYY)
		See also NONE, HOURLY, DAILY, WEEKLY,  MONTHLY AND YEARLY in this module
	"""
	now = datetime.datetime.now(tzlocal())
	stamp = None
	if timestamping == NONE:
		stamp = None
	elif timestamping == HOURLY:
		stamp = now.strftime("%Y.%m.%d.%H")
	elif timestamping == DAILY:
		stamp = now.strftime("%Y.%m.%d")
	elif timestamping == WEEKLY:
		stamp = now.strftime("%Y.%W")
	elif timestamping == MONTHLY:
		stamp = now.strftime("%Y.%m")
	elif timestamping == YEARLY:
		stamp = now.strftime("%Y")
	else:
		raise TypeError("Invalid timestamping selected")

	if stamp is None:
		return basename
	else:
		return "{0}-{1}".format(basename, stamp)

def create_river_config(river, name, config, host="localhost", port=9200):
	"""
	Saves the given Elasticsearch River configuration in Elasticsearch.

	The given river type and name are formatted like "$river-$name" to form the type name.

	Arguments
	---------
	river: string
		Name of the River plugin to use.
	name: string
		Name of this instance of the River plugin.
	config: JSON-formatted string or dict
		Configuration of the River. The contents is not validated, and passed as-is to Elasticsearch.
	host: string
		Elasticsearch host to connect to, defaults to localhost.
	port: int
		Elasticsearch port to connect to, defaults to 9200.
	"""
	es = Elasticsearch(hosts=[{ "host": host, "port": port }])
	es.index(index="_river", doc_type="{0}-{1}".format(river, name), body=config, id="_meta")

def delete_river_config(river, name, host="localhost", port=9200):
	"""
	Removes the given Elasticsearch River configuration from Elasticsearch.

	The given river type and name are formatted like "$river-$name" to form the type name.

	Arguments
	---------
	river: string
		Name of the River plugin to use.
	name: string
		Name of this instance of the River plugin.
	host: string
		Elasticsearch host to connect to, defaults to localhost.
	port: int
		Elasticsearch port to connect to, defaults to 9200.
	"""
	es = Elasticsearch(hosts=[{ "host": host, "port": port }])
	es.delete(index="_river", doc_type="{0}-{1}".format(river, name), id=None)

class BulkMessage(object):
	"""
	Message formatter for using the Elasticsearch Bulk API

	See also: http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/docs-bulk.html
	"""

	def __init__(self, index, message=None, action=INDEX_ACTION, datatype=None, id=None, encode_message=True):
		"""
		Initialize a BulkMessage, and set all properties.

		Parameters
		----------
		index: string
			What index to manipulate.
		message: string, dict, list of strings or list of dicts
			Either a:
			- JSON formatted message. Be sure to set encode_message to False.
			- dict. Will be JSON encoded as a single message.
			- list of JSON formatted messages. Be sure to set encode_message to False.
			- list of dicts. Will be individually encoded as a message, and bulk processed in the same action.

			When using a list, the id parameter is non-applicable.
		action: string
			What action to perform. See also the INDEX_ACTION, CREATE_ACTION, DELETE_ACTION, UPDATE_ACTION module
			constants. Defaults to INDEX_ACTION.
		datatype: string
			What Elasticsearch type mapping to use. Mandatory.
		id: string
			What ID to index this message under. Optional, by default Elasticsearch will generate a new ID for all
			indexed messages. Not applicable when using a list of dicts as input.
		encode_message: boolean
			Set to True if the message is a non-JSON encoded dict.
			Set to False if the message is already a JSON encoded string.
		"""

		metadata = {}
		metadata["_index"] = index
		if datatype:
			metadata["_type"] = datatype
		if id:
			metadata["_id"] = id

		self.action = action
		self.metadata = {}
		self.metadata[action] = metadata

		self.encode = encode_message
		self.message = message

	def generate(self, as_objects=False):
		"""
		Generate a JSON formatted Bulk API message, using the stored data in this BulkMessage.

		Parameters
		----------
		as_objects: boolean
			If True, this method will return tuples containing (metadata, message), instead of
			a single string of information. Both entries are strings ending in a newline, and will form a
			valid Elasticsearch Bulk API message when concatenated together.
		"""

		metadata = "{0}".format(json.dumps(self.metadata))
		if self.action == DELETE_ACTION:
			if as_objects:
				return (metadata + "\n", "")
			else:
				return metadata + "\n"

		if not self.message:
			raise TypeError("Message was not specified")

		message_list = []

		if isinstance(self.message, (list, tuple)):
			if self.encode:
				message_list = map(lambda x: json.dumps(x) + "\n", self.message)
			else:
				message_list = map(lambda x: x + "\n", self.message)
		elif self.encode:
			message_list = [ json.dumps(self.message) + "\n" ]
		else:
			message_list = [ self.message + "\n" ]

		metadata_list = [ metadata + "\n" ] * len(message_list)
		full_message = zip(metadata_list, message_list)

		if as_objects:
			return full_message
		else:
			full_message = map(lambda x: "".join(x), full_message)
			return "".join(full_message)
