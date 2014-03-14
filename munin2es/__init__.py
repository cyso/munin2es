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

NAME = "munin2es"
VERSION = "0.1"
BUILD = "AAAAA"

import logging, logging.handlers, os, pwd, grp, sys, inspect, tempfile

def getLogger(name, level=logging.INFO, handlers=[]):
	logger = logging.getLogger(name)

	if len(handlers) != 0:
		logger.setLevel(level)

	if "console" in handlers:
		strm = logging.StreamHandler()
		fmt = logging.Formatter('%(message)s')
		strm.setLevel(level)
		strm.setFormatter(fmt)
		logger.addHandler(strm)

	if "file" in handlers:
		conf = handlers['file']
		fl = logging.handlers.WatchedFileHandler(conf['logfile'])
		fl.setLevel(level)

		fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fl.setFormatter(fmt)
		logger.addHandler(fl)

	if "syslog" in handlers:
		sysl = logging.handlers.SysLogHandler(address='/dev/log', facility=logging.handlers.SysLogHandler.LOG_SYSLOG)
		sysl.setLevel(level)

		formatter = logging.Formatter('%(name)s[' + str(os.getpid()) + '] %(levelname)-8s: %(message)s')
		sysl.setFormatter(formatter)
		logger.addHandler(sysl)

	return logger

