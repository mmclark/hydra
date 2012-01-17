#!/usr/bin/env python
#
# Hydra SQL Diff Program - maintain diff/patch state in database
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

if __name__ == '__main__':
  # Configure logging first so log.warning works when importing modules
  import logging as log, tornado.options
  from tornado.options import define, options
  if options.logging != 'none':
    log.getLogger().setLevel(getattr(log, options.logging.upper()))
    tornado.options.enable_pretty_logging()

import commands
import datetime
import getpass
import glob
import operator
import optparse
import os
import pprint
import sys
import traceback
import tornado.database
import topology
import stdlib

# Command line options
def opts():
  p = optparse.OptionParser()
  p.add_option("-a", metavar='<app_name>', dest="app_name", action="store",
               default=False, help="required: application name")
  p.add_option("-c", dest="create", action="store_true",
               default=False, help="create schema")
  p.add_option("-e", metavar='<env>', dest="env", action="store",
               default=False, help="required: environment [local, pearl] - or set HYDRA_ENV")
  (opts, args) = p.parse_args()
  return (opts, args, p)

# Abort early if options not set properly
(opts, args, optparser) = opts()
env = os.getenv('HYDRA_ENV')
if not env:
  env = opts.env
if not opts.app_name or not env:
  optparser.print_help()
  sys.exit(1)
schema = opts.app_name
if '/' in schema:
  schema = schema.split('/')[1]

# Just create the database
if opts.create:
  host = topology.getenv(schema+'_mysql_host')
  user = topology.getenv(schema+'_mysql_user')
  schema_password = topology.getenv(schema+'_mysql_password')
  print stdlib.cstr('MySQL root password:', 'green'),
  stdlib.conceal()
  try:
    password = getpass.getpass('')
  finally:
    stdlib.reveal()
  print
  try:
    db = tornado.database.Connection(host, 'mysql', 'root', password)
    sql = 'CREATE DATABASE IF NOT EXISTS %s' % schema
    db.execute(sql)
    sql = "GRANT ALL PRIVILEGES ON %s.* TO '%s'@'%s' IDENTIFIED BY '%s'"
    sql = sql % (schema, user, host, schema_password)
    db.execute(sql)
    log.info('Database was created successfully. Now re-run schema.py without -c')
  except:
    log.error('DB creation failed. Did you set up topology?')
    log.error(traceback.format_exc())
  sys.exit(0)

# Support
try:
  host = topology.getenv(schema+'_mysql_host')
  user = topology.getenv(schema+'_mysql_user')
  passwd = topology.getenv(schema+'_mysql_password')
  db = tornado.database.Connection(host, schema, user, passwd)
except tornado.database.OperationalError, e:
  log.warning("The database doesn't exist. Try -c <schema> option.")

def diff_sort_cmp(x, y):
  xx = int(x.split('diff')[1].split('.sql')[0])
  yy = int(y.split('diff')[1].split('.sql')[0])
  return xx - yy

def sql_diff_apply(diff_name):
  sql = 'UPDATE sql_diff SET applied=NOW() WHERE diff_name=%s'
  return db.execute(sql, diff_name)

def sql_diff_create(diff_name):
  sql = 'INSERT IGNORE INTO sql_diff (diff_name, created) VALUES (%s, NOW())'
  return db.execute(sql, diff_name)

def sql_diff_scan():
  sql = 'SELECT * FROM sql_diff ORDER BY rank ASC'
  return db.query(sql)

def sql_diff_scan_unapplied():
  sql = 'SELECT * FROM sql_diff WHERE applied IS NULL ORDER BY rank ASC'
  return db.query(sql)

def patch_filenames(sql_dir, prefix='diff'):
  if not os.path.exists(sql_dir):
    log.error('No patch dir found at: %s', sql_dir)
    sys.exit(1)
  patches = [g.split('/')[-1] for g in glob.glob(sql_dir + '/' + prefix + '*.sql')]
  patchnums = [int(patch.lstrip(prefix).rstrip('.sql')) for patch in patches]
  patchnums.sort()
  filenames = ['%s/%s%s.sql' % (sql_dir, prefix, patchnum) for patchnum in patchnums]
  filenames = sorted(filenames, cmp=diff_sort_cmp)
  return filenames

# Main

# check if sql_diff table exists
sql = "SHOW TABLE STATUS LIKE 'sql_diff'"
if not db.get(sql):
  sql_diff = """
  CREATE TABLE IF NOT EXISTS sql_diff (
    diff_name VARCHAR(80) NOT NULL,
    created datetime NOT NULL,
    applied datetime DEFAULT NULL,
    rank int NOT NULL auto_increment,
    PRIMARY KEY (diff_name),
    KEY position_nbr (rank)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
  """
  db.execute(sql_diff)

# determine which patches need applied, and apply them
hydra_sql_dir = 'sql'
filenames = patch_filenames(hydra_sql_dir)
if topology.getenv('%s_dir' % schema):
  app_sql_dir = topology.getenv('%s_dir' % schema) + '/sql'
else:
  app_sql_dir = os.path.join(schema, 'sql')
if not os.path.realpath(app_sql_dir) == os.path.realpath(hydra_sql_dir):
  filenames += patch_filenames(app_sql_dir)

# filter out patches already inserted into db
db_patch_names = [d['diff_name'] for d in sql_diff_scan()]
files = [fn for fn in filenames if fn not in db_patch_names]

# insert them into the db
for fn in files:
  sql_diff_create(fn)
for patch in sql_diff_scan_unapplied():
  sql = open(patch['diff_name']).read()
  db.execute(sql)
  sql_diff_apply(patch['diff_name'])
