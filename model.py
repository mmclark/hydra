# Share database schema/code
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

import inspect, pprint, threading, time, traceback
import tornado.database, tornado.escape
import log, stdlib, topology


# Database libraries
def get_request_handler():    #  This function is very slow
  f = inspect.currentframe()
  while (f):
    info = inspect.getframeinfo(f)
    if inspect.getmodulename(info[0]) == 'web' and info[2] == '_execute':
      reqh = f.f_locals['self']
      return reqh
    f = f.f_back

dbconns = {}
def db_connect(**kwargs):
  global dbconns
  # which schema to connect
  schema = kwargs.get('schema', None)
  if not schema:
    schema = get_request_handler()._schema
  host = topology.getenv(schema+'_mysql_host')
  user = topology.getenv(schema+'_mysql_user')
  passwd = topology.getenv(schema+'_mysql_password')
  # force a new connection
  if kwargs.get('force', False):
    return tornado.database.Connection(host, schema, user, passwd)
  # check existing connections
  ident = threading.current_thread().ident
  dbconn = dbconns.get(ident, {})
  if schema not in dbconn:
    dbconn[schema] = tornado.database.Connection(host, schema, user, passwd)
    dbconns[ident] = dbconn
  return dbconn[schema]

def db_disconnect():
  global dbconns
  ident = threading.current_thread().ident
  if ident in dbconns:
    for dbconn in dbconns[ident].keys():
      del dbconns[ident][dbconn]

def retry(func, query, *args, **kwargs):
  retry = 0
  while retry < 2:
    try:
      return func(query, *args, **kwargs)
    except tornado.database.OperationalError, oe:
      traceback.print_exc()
      retry += 1
      log.warning('Retry #%d' % retry)
      time.sleep(1)
  raise Exception("Couldn't connect to database")

def db_exec(query, *args, **kwargs):
  return retry(db_connect(**kwargs).execute, query, *args, **kwargs)

def db_get(query, *args, **kwargs):
  return retry(db_connect(**kwargs).get, query, *args, **kwargs)

def db_iter(query, *args, **kwargs):
  return retry(db_connect(force=True, **kwargs).iter, query, *args, **kwargs)

def db_query(query, *args, **kwargs):
  return retry(db_connect(**kwargs).query, query, *args, **kwargs)


# Sessions
def put_session(session_md5, session):
  session.save()
  data = tornado.escape.json_encode(session)
  if db_get('SELECT session_md5 FROM session WHERE session_md5=%s', session_md5):
    sql = 'UPDATE session SET data=%s WHERE session_md5=%s'
    db_exec(sql, data, session_md5)
  else:
    sql = 'INSERT INTO session (session_md5, data) VALUES (%s, %s)'
    db_exec(sql, session_md5, data)

def get_session(session_md5):
  sql = 'SELECT * FROM session WHERE session_md5=%s'
  session = db_get(sql, session_md5)
  if session and 'data' in session:
    return tornado.escape.json_decode(session['data'])
  return None

def delete_session(session_md5):
  return db_exec('DELETE FROM session WHERE session_md5=%s', session_md5)


# Member Database
def member_create(username, password_bcrypt):
  if member_read(username):
    return False
  sql = 'INSERT INTO member (username, password_bcrypt, created) VALUES (%s, %s, NOW())'
  return db_exec(sql, username, password_bcrypt)

def member_create_email(email, remote_ip):
  if member_read_by_email(email):
    return False
  sql = 'INSERT INTO member (email, created, created_ip) VALUES (%s, NOW(), %s)'
  member_id = db_exec(sql, email, remote_ip)
  if not member_id:
    return False
  # XXX looks like a bug to me
  verify_token = stdlib.md5hex(email+stdlib.bcrypt_salt())
  sql = 'INSERT INTO email (email, created, verify_token) VALUES (%s, NOW(), %s)'
  return db_exec(sql, email, verify_token[:16])

def member_read_by_email(email):
  return db_get('SELECT * FROM member WHERE email=%s', email)

def member_read(username):
  return db_get('SELECT * FROM member WHERE username=%s', username)

def member_get_by_id(member_id):
  return db_get('SELECT * FROM member WHERE member_id=%s', member_id)

def member_get(username):
  return member_read(username)

def member_get_id(username):
  member = member_get(username)
  if member:
    return member['member_id']

def change_password(username, password_bcrypt, password_crypt):
  member_id = get_member(username)['member_id']
  db_exec('UPDATE member SET password_bcrypt=%s WHERE username=%s', password_bcrypt, username)

def delete_member(username):
  member_id = get_member(username)['member_id']
  db_exec('UPDATE member SET deleted=NOW() WHERE username=%s', username)

def undelete_member(username):
  member_id = get_member(username)['member_id']
  db_exec('UPDATE member SET deleted=NULL WHERE username=%s', username)

def expunge_member(username):
  db_exec('DELETE FROM member WHERE username=%s', username)

def get_members():
  return db_query('SELECT * FROM member')

def check_password(username, password_bcrypt):
  member = get_member(username)
  return password_bcrypt == member['password_bcrypt']

def member_update_marketing_id(member_id, marketing_id):
  sql = 'UPDATE member SET marketing_id=%s WHERE member_id=%s'
  return db_exec(sql, marketing_id, member_id)


def email_read(email):
  sql = 'SELECT * FROM email WHERE email=%s'
  return db_get(sql, email)
