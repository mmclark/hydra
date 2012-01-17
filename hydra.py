# Hydra Handler
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Imports
import pprint, traceback, xml.sax.saxutils
import tornado.escape, tornado.web
import log, model, stdlib, topology, uimethods, mail


# Handlers
class Hydra(tornado.web.RequestHandler):
  def __init__(self, *args, **kwargs):
    super(Hydra, self).__init__(*args, **kwargs)
    self._domain = self.request.headers['Host'].split(':')[0]
    self._app_name = schema = self._domain.split('.')[1]
    if not topology.getenv(schema+'_mysql_host'):
      schema = 'hydra'
    self._schema = schema
    self.tmpl = {}
    self.tmpl['domain'] = self._domain
    self.tmpl['schema'] = self._schema
    self.tmpl['app_name'] = self._app_name
    self.tmpl['user_agent'] = self.request.headers.get('User-Agent')
    self.tmpl['scheme'] = 'http://'
    self.use_session = True
    self.session_expiry = 1
    self.auth_method = 'username_password'
    self.auth_expiry = 30

  def cookie_encode(self, val):
    return tornado.escape.url_escape(tornado.escape.json_encode(val))

  def cookie_decode(self, val):
    if val is None:
      return {}
    ck = tornado.escape.json_decode(tornado.escape.url_unescape(val))
    if type(ck) is dict:
      ck = dict([(str(key), ck[key]) for key in ck])
    return ck

  def html_escape(self, val):
    return xml.sax.saxutils.escape(val, {'"': '&quot;'})

  def respond_json(self, json_str):
    self.write(tornado.escape.json_encode(json_str))
    self.set_header('Content-Type', 'application/json')
    self.finish()

  def _handle_request_exception(self, e):
    if topology.env != 'local' and not isinstance(e, tornado.web.HTTPError):
      # if we're not developing locally, send an email
      mail.error_email(self._domain, self)
    super(Hydra, self)._handle_request_exception(e)

  def session_start(self):
    session_ck = self.get_secure_cookie('session')
    if session_ck:
      session = model.get_session(session_ck)
      if session:
        self.session = stdlib.Session(session)
    if not hasattr(self, 'session'):
      self.session = stdlib.Session(salt=self.request.headers)
      model.put_session(self.session['id'], self.session)
    self.set_secure_cookie('session', self.session['id'], expires_days=self.session_expiry)
    self.tmpl['session'] = self.session

  def session_end(self):
    self.clear_cookie('session')
    self.clear_cookie('auth')
    model.delete_session(self.session['id'])

  def auth_start(self, credentials):
    if self.session is None:
      return False
    if self.auth_method == 'email_token' and credentials:
      # XXX verify that email hashes to the token
      email = credentials['email']
      if credentials['verify_token'] == credentials['token']:
        self.set_secure_cookie('auth', self.cookie_encode(credentials), expires_days=1)
        if self.use_session:
          self.session['email'] = credentials['email']
          member = model.member_read_by_email(email)
          self.session['member_id'] = member['member_id']
          self.session['username'] = member['username']
    if self.auth_method == 'username_password' and credentials:
      username = credentials.get('username', None)
      if not username:
        username = credentials.get('signup_user', None)
      if username:
        credentials['username'] = username
        self.set_secure_cookie('auth', self.cookie_encode(credentials), expires_days=1)
        if self.use_session:
          self.session['username'] = username
          self.session['member_id'] = model.member_get_id(username)

  def auth_cookie(self):
    return self.cookie_decode(self.get_secure_cookie('auth'))

  def auth_end(self):
    self.clear_cookie('auth')
    if self.session:
      for delkey in ('username', 'member_id', 'email'):
        if delkey in self.session:
          del self.session[delkey]

  def get_current_user(self):
    if hasattr(self, 'session') and self.session:
      # this should check credentials type
      if self.session.get('username'):
        return self.session['username']
      if self.session.get('email'):
        return self.session['email']
    return None

  def set_options_cookie(self, opts):
    self.set_secure_cookie('options', self.cookie_encode(opts), expires_days=365)

  def get_options_cookie(self):
    return self.cookie_decode(self.get_secure_cookie('options'))

  def prepare(self):
    self.set_header('Cache-Control', 'no-cache')
    self.set_header('Pragma', 'no-cache')
    self.set_header('Expires', 'Sat, 10 Jun 2006 03:08:13 GMT')
    self.page_name = '%s.%s' % (self.__class__.__name__, self.request.method)
    self.tmpl['page_name'] = self.page_name
    self.request.args = {}
    for key, value in self.request.arguments.iteritems():
      self.request.args[key] = value[0]
    if self.use_session:
      self.session_start()
      self.auth_start(self.auth_cookie())

  def finish(self, chunk=None):
    if self.page_name and not self.page_name.startswith('Logout'):
      auth_ck = self.auth_cookie()
      if auth_ck:
        self.set_secure_cookie('auth', self.cookie_encode(auth_ck), expires_days=self.auth_expiry)
    if self.use_session and self.session.dirty():
      model.put_session(self.session['id'], self.session)
    tornado.web.RequestHandler.finish(self, chunk)

  def directory_scan(self):
    dirnames = [self._domain]
    dirname = self._domain
    if dirname.startswith('local.'):
      dirname = self._domain[6:]
      dirnames.append(dirname)
    if dirname.endswith('.com') or dirname.endswith('.net') or dirname.endswith('.org'):
      dirname = dirname[:-4]
      dirnames.append(dirname)
    return dirnames

  def render_scan(self, filename):
    for dirname in self.directory_scan():
      try:
        self.render(dirname+'/'+filename, **self.tmpl)
        return True
      except IOError, ex:
        log.error(traceback.print_exc())
      except:
        log.error(traceback.print_exc())

class Index(Hydra):
  def get(self):
    # see if there's a specific site override
    if self.render_scan('index.html'):
      return
    # try to serve up the standard hydra page, overwise print domain name
    try:
      return self.render('index.html', **self.tmpl)
    except IOError, ex:
      if 'No such file or directory' in ex:
        self.write(self._domain)

  def head(self):
    pass
  

class Logout(Hydra):
  def get(self):
    self.auth_end()
    self.session_end()
    self.redirect('/')

  def post(self):
    self.auth_end()
    self.session_end()
    self.redirect('/')
