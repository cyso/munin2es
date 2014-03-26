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
import logging, logging.handlers, os
from chaos.logging import get_logger
from .muninnode import MuninNodeClient
from .elasticsearch import BulkMessage

NAME = "munin2es"
VERSION = "0.1"
BUILD = "AAAAA"

def process_munin_client(node, port=4949):
	client = MuninNodeClient(node, port)
	messages = client.get_all_messages(preformat=True)

	bulk = BulkMessage(index="munin-2014.03.25", message=messages, encode_message=False, datatype="munin")

	print bulk.generate()

def hello(text):
	get_logger(__name__).info(text)
