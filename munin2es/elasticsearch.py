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

INDEX_ACTION = "index"
CREATE_ACTION = "create"
DELETE_ACTION = "delete"
UPDATE_ACTION = "update"

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
			What Elasticsearch type mapping to use. Optional.
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

		self.metadata = {}
		self.metadata[action] = metadata

		self.encode = encode_message
		self.message = message

	def generate(self):
		"""
		Generate a JSON formatted Bulk API message, using the stored data in this BulkMessage.
		"""

		message = ""
		if self.action == DELETE_ACTION:
			return "{0}\n".format(json.dumps(self.metadata))

		if not self.message:
			raise TypeError("Message was not specified")

		if isinstance(self.message, (list, tuple)):
			if self.encode:
				tmp = "\n".join(map(lambda x: json.dumps(x), self.message))
			else:
				tmp = "\n".join(self.message)
		elif self.encode:
			tmp = json.dumps(self.message)
		else:
			tmp = self.message

		message = "{0}\n{1}\n".format(json.dumps(self.metadata), tmp)

		return message
