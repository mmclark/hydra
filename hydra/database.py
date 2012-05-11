# Extension of Tornado Database
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Python Imports
import logging as log
import pprint
import threading
import time
import traceback

# Extern Imports
import tornado.database
import tornado.escape
from tornado.options import options


# Maintains a thread-safe dict of connections to databases
class Connection(tornado.database.Connection):
    threads = {}

    @classmethod
    def connect(cls, **kwargs):
        if 'mysql_schema' in kwargs:
            host = kwargs['mysql_host']
            schema = kwargs['mysql_schema']
            user = kwargs['mysql_user']
            passwd = kwargs['mysql_password']
        else:
            host = options.mysql_host
            schema = options.mysql_schema
            user = options.mysql_user
            passwd = options.mysql_password
        # force a new connection
        if kwargs.get('force', False):
            return cls(host, schema, user, passwd)
        # check existing connections
        ident = threading.current_thread().ident
        connections = cls.threads.setdefault(ident, {})
        if not schema in connections:
            conn = cls(host, schema, user, passwd)
            conn.schema = schema
            cls.threads[ident][schema] = conn
        return connections[schema]

    def retry(self, func, query, *args, **kwargs):
        retry = 0
        while retry < 2:
            try:
                return func(query, *args)
            except tornado.database.OperationalError, oe:
                if 'Unknown column' in oe.args[1]:
                    raise
                else:
                    traceback.print_exc()
                    retry += 1
                    log.warning('Retry #%d' % retry)
                    time.sleep(1)
        raise

    def query(self, sql, *args, **kwargs):
        db_query = super(Connection, self).query
        results = self.retry(db_query, sql, *args, **kwargs)
        if kwargs.get('cls'):
            results = [kwargs['cls'](r) for r in results]
        return results

    def get(self, sql, *args, **kwargs):
        db_get = super(Connection, self).get
        row = self.retry(db_get, sql, *args, **kwargs)
        if row and kwargs.get('cls'):
            row = kwargs['cls'](row)
        return row

    def execute(self, sql, *args, **kwargs):
        db_execute = super(Connection, self).execute
        return self.retry(db_execute, sql, *args, **kwargs)

    def iter(self, sql, *args, **kwargs):
        db_iter = super(Connection, self).iter
        for row in self.retry(db_iter, sql, *args, **kwargs):
            if kwargs.get('cls'):
                row = kwargs['cls'](row)
            yield row

class Row(tornado.database.Row):
    pass
