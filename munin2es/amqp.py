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

import munin2es
import pika
from pika.exceptions import AMQPConnectionError, ChannelClosed

NORMAL_MESSAGE = 1
PERSISTENT_MESSAGE = 2

class Queue(object):
	""" Holds a connection to an AMQP queue, and methods to publish to it. """
	def __init__(self, host, credentials, exchange, routing_key):
		"""
		Initialize queue and configure connection.

		Parameters
		----------
		host: tuple 
			Must contain hostname and port to use for connection
		credentials: tuple
			Must contain username and password for this connection
		exchange: dict 
			Must contain at least the following keys:
			exchange: string - what exchange to use
			exchange_type: string - what type of exchange to use ("direct")
			passive: boolean - should we use an existing exchange, or try to declare our own
			  options below are optional when passive = True
			durable: boolean - should the queue be durable
			auto_delete: boolean - should we auto delete the queue when we close the connection
		routing_key: string
			what routing_key to use for published messages. If unset, this parameter must be set during publishing
		"""

		self.default_routing_key = routing_key
		self.credentials = pika.PlainCredentials(credentials[0], credentials[1])
		self.parameters = pika.ConnectionParameters(host=host[0], port=host[1], credentials=self.credentials)
		self.connection = pika.BlockingConnection(self.parameters)
		self.channel = self.connection.channel()

		self.exchange_name = exchange['exchange']
		try:
			self.channel.exchange_declare(**exchange)
		except ChannelClosed, e:
			raise Exception(str(e[1]))
	
	def close(self):
		self.connection.close()
	
	def publish(self, message, properties={}):
		"""
		Publish a message to an AMQP exchange.

		Parameters
		----------
		message: string
			Message to publish.
		properties: dict
			Properties to set on message. This parameter is optional, but all options must be set if specified:
			routing_key: string - what routing_key to use. MUST be set if this was not set during __init__.
			content_type: string - what content_type to specify, default is 'text/plain'.
			delivery_mode: int - what delivery_mode to use. By default message are not persistent, but this can be 
				set by specifying PERSISTENT_MESSAGE .
		"""
		routing_key = self.default_routing_key
		if properties and "routing_key" in properties:
			routing_key = properties["routing_key"]
			del(properties["routing_key"])

		if not routing_key:
			raise Exception("routing_key was not specified")

		self.channel.basic_publish(self.exchange_name, routing_key, message, pika.BasicProperties(**properties))
