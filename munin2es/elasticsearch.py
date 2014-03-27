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

import json, datetime
from dateutil.tz import tzlocal

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

	def generate(self):
		"""
		Generate a JSON formatted Bulk API message, using the stored data in this BulkMessage.
		"""

		metadata = "{0}".format(json.dumps(self.metadata))
		if self.action == DELETE_ACTION:
			return metadata + "\n"

		if not self.message:
			raise TypeError("Message was not specified")

		if isinstance(self.message, (list, tuple)):
			if self.encode:
				message = "\n{0}\n".format(metadata).join(map(lambda x: json.dumps(x), self.message))
			else:
				message = "\n{0}\n".format(metadata).join(self.message)
		elif self.encode:
			message = json.dumps(self.message)
		else:
			message = self.message

		return "{0}\n{1}".format(metadata, message)
