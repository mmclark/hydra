# Network topology - manage different environments in software
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

import os, sys, syslog
import log

srcpath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if srcpath in sys.path:
  sys.path.remove(srcpath)
sys.path.insert(0, srcpath)

env = os.getenv('HYDRA_ENV')
user = os.getenv('USER')
if not env:
  log.error("HYDRA_ENV is not set")

environments = {
  'local': {
    'host': 'localhost',
    'basedir': '/home/%s/src' % user,
    'from_email': 'Hydra <you+hydra@domain.tld>',
    'to_email': 'you@domain.tld',
  },
  'dev': {
    'host': 'localhost',
    'basedir': '/srv',
  },
}

# Configurations that can go in all environments
for environ in environments:
  environments[environ]['cryptsalt'] = 's8dfUASD()F---8hydra12..;ZX00r8q'
  environments[environ]['port'] = 2098

  # Hydra isn't really an application, supply here for documentation
  environments[environ]['hydra_mysql_host'] = 'localhost'
  environments[environ]['hydra_mysql_schema'] = 'hydra'
  environments[environ]['hydra_mysql_user'] = 'hydra'
  environments[environ]['hydra_mysql_password'] = '8HYDRA8'
  environments[environ]['hydra_dir'] = '.'

  # Hello World
  environments[environ]['helloworld_mysql_host'] = 'localhost'
  environments[environ]['helloworld_mysql_schema'] = 'helloworld'
  environments[environ]['helloworld_mysql_user'] = 'helloworld'
  environments[environ]['helloworld_mysql_password'] = 'HI!!'
  environments[environ]['helloworld_dir'] = '.'


def getenv(env_var, default=False):
  return environments[env].get(env_var, default)
