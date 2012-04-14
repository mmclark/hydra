# Simplistic logging to syslog
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

import logging, pprint, sys, syslog, traceback

ident = 'hydra'
facility = syslog.LOG_LOCAL1

def make_msg(args):
  if type(args) not in (str, unicode):
    msg = ''
    for arg in args:
      if type(arg) is str:
        msg += arg
      elif type(arg) is unicode:
        msg += arg.encode('US-ASCII', 'xmlcharrefreplace')
      else:
        msg += str(arg)
      msg += ' '
      msg.strip()
      args = msg
  return args

def exception():
  msg = traceback.format_exc()
  if sys.stderr.isatty():
    logging.error(msg)
  syslog.openlog(ident, syslog.LOG_NDELAY, facility)
  syslog.syslog(syslog.LOG_ERR, msg)
  syslog.closelog()

def info(*args):
  msg = make_msg(args)
  if sys.stderr.isatty():
    logging.warning(msg)
  syslog.openlog(ident, syslog.LOG_NDELAY, facility)
  syslog.syslog(syslog.LOG_INFO, msg)
  syslog.closelog()

def warning(*args):
  msg = make_msg(args)
  if sys.stderr.isatty():
    logging.warning(msg)
  syslog.openlog(ident, syslog.LOG_NDELAY, facility)
  syslog.syslog(syslog.LOG_WARNING, msg)
  syslog.closelog()

def debug(*args):
  msg = make_msg(args)
  if sys.stderr.isatty():
    logging.debug(msg)
  syslog.openlog(ident, syslog.LOG_NDELAY, facility)
  syslog.syslog(syslog.LOG_DEBUG, msg)
  syslog.closelog()

def error(*args):
  msg = make_msg(args)
  if sys.stderr.isatty():
    logging.error(msg)
  syslog.openlog(ident, syslog.LOG_NDELAY, facility)
  syslog.syslog(syslog.LOG_ERR, msg)
  syslog.closelog()

def vardump(*args):
  warning(pprint.pformat(args[0]))
