# Hydra's central data model
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Python Imports
import logging as log
import pprint

# Extern Imports
import tornado.escape

# Project Imports
import database

class Session(database.Row):
    @staticmethod
    def put(session_md5, session):
        conn = database.Connection.connect()
        session.save()
        data = tornado.escape.json_encode(session)
        if conn.get('SELECT session_md5 FROM session WHERE session_md5=%s', session_md5):
            sql = 'UPDATE session SET data=%s WHERE session_md5=%s'
            conn.execute(sql, data, session_md5)
        else:
            sql = 'INSERT INTO session (session_md5, data, created) VALUES (%s, %s, NOW())'
            conn.execute(sql, session_md5, data)
    
    @staticmethod
    def get(session_md5):
        conn = database.Connection.connect()
        sql = 'SELECT * FROM session WHERE session_md5=%s'
        session = conn.get(sql, session_md5)
        if session and 'data' in session:
            return tornado.escape.json_decode(session['data'])
        return None
    
    @staticmethod
    def delete(session_md5):
        conn = database.Connection.connect()
        return conn.execute('DELETE FROM session WHERE session_md5=%s', session_md5)
