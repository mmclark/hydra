#!/usr/bin/env python
#
# Hydra Schema Management Program
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

# Configure Logging
import logging as log
import tornado.options
from tornado.options import define, options
if options.logging != 'none':
    log.getLogger().setLevel(getattr(log, options.logging.upper()))
    tornado.options.enable_pretty_logging()

# Python Imports
import getpass
import glob
import os
import pprint
import sys
import traceback

# Extern Imports
import tornado.database
import MySQLdb

# Project Imports
import stdlib


# Command line options - abort early if options not set properly
define('app', default=None, help='[Required] Application name', type=str)
define('create', default=None, help='Create schema', type=bool)
define('env', default=None, help='Environment [local, quartz] - or set HYDRA_ENV', type=str)
tornado.options.parse_command_line()
env = os.getenv('HYDRA_ENV')
if not env:
    env = options.env
if not options.app or not env:
    tornado.options.print_help()
    sys.exit(1)
__import__("%s.config" % options.app)
schema = options.mysql_schema


# Just create the database
if options.create:
    host = options.mysql_host
    user = options.mysql_user
    schema_password = options.mysql_password
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
        log.info('Database was created successfully. Now re-run schema.py without --create')
    except:
        log.error('DB creation failed. Did you set up config?')
        log.error(traceback.format_exc())
    sys.exit(0)


# Support
def diff_sort_cmp(x, y):
    xx = int(x.split('diff')[1].split('.sql')[0])
    yy = int(y.split('diff')[1].split('.sql')[0])
    return xx - yy

def sql_diff_apply(diff_type, diff_name):
    sql = 'UPDATE sql_diff SET applied=NOW() WHERE diff_type=%s AND diff_name=%s'
    return db.execute(sql, diff_type, diff_name)

def sql_diff_create(diff_type, diff_name):
    sql = 'INSERT IGNORE INTO sql_diff (diff_type, diff_name, created) VALUES (%s, %s, NOW())'
    return db.execute(sql, diff_type, diff_name)

def sql_diff_scan():
    sql = 'SELECT * FROM sql_diff ORDER BY diff_type, diff_name ASC'
    return db.query(sql)

def sql_diff_scan_unapplied():
    sql = """SELECT * FROM sql_diff WHERE diff_type=%s AND applied IS NULL
             ORDER BY diff_type, SUBSTRING_INDEX(diff_name, 'diff', 0) ASC"""
    hydra_rows = db.query(sql, 'hydra')
    app_rows = db.query(sql, options.app)
    return hydra_rows + app_rows

def patch_diffs(sql_dir, prefix='diff'):
    if not os.path.exists(sql_dir):
        log.error('No patch dir found at: %s', sql_dir)
        sys.exit(1)
    patches = [g.split('/')[-1] for g in glob.glob(sql_dir + '/' + prefix + '*.sql')]
    patchnums = [int(patch.lstrip(prefix).rstrip('.sql')) for patch in patches]
    patchnums.sort()
    diffs = ['%s%s.sql' % (prefix, patchnum) for patchnum in patchnums]
    diffs = sorted(diffs, cmp=diff_sort_cmp)
    return diffs


def main():
    # check if sql_diff table exists
    sql = "SHOW TABLE STATUS LIKE 'sql_diff'"
    if not db.get(sql):
        sql_diff = """
        CREATE TABLE IF NOT EXISTS sql_diff (
            diff_type VARCHAR(80) NOT NULL,
            diff_name VARCHAR(80) NOT NULL,
            created datetime NOT NULL,
            applied datetime DEFAULT NULL,
            PRIMARY KEY (diff_type, diff_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
        """
        db.execute(sql_diff)

    # determine potential patch filenames
    sql_dirs = {}
    sql_dirs['hydra'] = stdlib.absdir(__file__) + '/sql'
    sql_dirs[options.app] = options.basedir + '/sql'
    diffs = {}
    diffs['hydra'] = patch_diffs(sql_dirs['hydra'])
    if not os.path.realpath(sql_dirs[options.app]) == os.path.realpath(sql_dirs['hydra']):
        diffs[options.app] = patch_diffs(sql_dirs[options.app])

    # Filter out applied patches, insert unknown patches into sql_diff table
    db_patch_names = {}
    for diff in sql_diff_scan():
        db_patch_names.setdefault(diff['diff_type'], []).append(diff['diff_name'])
    for diff_type in diffs:
        for diff_name in diffs[diff_type]:
            if diff_name in db_patch_names.get(diff_type, []):
                continue
            sql_diff_create(diff_type, diff_name)

    # apply the unapplied patches
    for patch in sql_diff_scan_unapplied():
        filename = os.path.join(sql_dirs[patch['diff_type']], patch['diff_name'])
        sql = open(filename).read()
        try:
            db.execute(sql)
        except MySQLdb.ProgrammingError, ex:
            if ex.args[0] == 2014 and ex.args[1].startswith('Commands out of sync'):
                log.error("Absorbing MySQLdb warnings on multiple-query sql statement.")
                log.error("Please verify that your patch went through successfully.")
                log.error("Reconnecting...")
                log.error("Ignore OperationalError (2013, Lost connection to MySQL)")
                db.reconnect()
        log.warning("Applying patch:  %s / %s" % (patch['diff_type'], patch['diff_name']))
        sql_diff_apply(patch['diff_type'], patch['diff_name'])


# Main
if __name__ in ('__main__', 'hydra.schema'):
    try:
        host = options.mysql_host
        user = options.mysql_user
        password = options.mysql_password
        db = tornado.database.Connection(host, schema, user, password)
        db.get("SHOW TABLE STATUS like 'sql_diff'")
    except tornado.database.OperationalError, e:
        log.error("The database doesn't exist. Try -c option.")
    main()
