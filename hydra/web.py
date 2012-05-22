#!/usr/bin/env python
#
# Hydra Daemon
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Environment
#if __name__ == '__main__':
import logging as log, tornado.options   # Configure logging first so works in imports
from tornado.options import define, options
if options.logging != 'none':
    log.getLogger().setLevel(getattr(log, options.logging.upper()))
    tornado.options.enable_pretty_logging()
import os
env = os.getenv('HYDRA_ENV')


# Python Imports
import pprint
import time
import traceback
import xml.sax.saxutils

# Extern Imports
import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import options
import tornado.escape
import tornado.web

# Project Imports
import uimethods
import database
import stdlib
import mail
import model


# Application
class Application(tornado.web.Application):
    def __init__(self):
        settings = dict(
          cookie_secret=options.cookie_secret,
          xsrf_cookies=True,
          debug=True,
          login_url='/',
          ui_methods=[uimethods],
        )
        if 'template_path' in options:
            settings['template_path'] = options.template_path
        if 'static_path' in options:
            settings['static_path'] = options.static_path

        tornado.web.Application.__init__(self, **settings)

  #def setup_handlers(self):
    #self.add_handlers(r".*helloworld\.com", helloworld.handlers.handler_urls)

    @staticmethod
    def start(application):
        http_server = tornado.httpserver.HTTPServer(application, xheaders=True,
                                                    no_keep_alive=True)
        log.info('listening on %s:%s' % (options.host, options.port))
        http_server.listen(options.port, address=options.host)
        tornado.ioloop.IOLoop.instance().start()
        

# Session Handler
class Session(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        if kwargs.get('salt') and not kwargs.get('id'):
            self['id'] = stdlib.md5hex('%10.13f %s' % (time.time(), kwargs['salt']))
        self._modified = False

    def __setitem__(self, key, value):
        self._modified = True
        super(Session, self).__setitem__(key, value)

    def __delitem__(self, key):
        self._modified = True
        super(Session, self).__delitem__(key)

    def dirty(self):
        return self._modified

    def save(self):
        self._modified = False

    def update(self, *args, **kwargs):
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, got %d" % len(args))
            other = dict(args[0])
            for key in other:
                self[key] = other[key]
        for key in kwargs:
            self[key] = kwargs[key]

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]


# Handlers
class RequestHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(RequestHandler, self).__init__(*args, **kwargs)
        self._domain = self.request.headers['Host'].split(':')[0]
        self._app_name = schema = self._domain.split('.')[1]
        #if not topology.getenv(schema+'_mysql_host'):
        #    schema = 'hydra'
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
        if env not in (options.local_envs) and not isinstance(e, tornado.web.HTTPError):
            # if we're not developing locally, send an email
            mail.error_email(self._domain, self)
        super(RequestHandler, self)._handle_request_exception(e)

    def session_start(self):
        session_ck = self.get_secure_cookie('session')
        if session_ck:
            session = model.Session.get(session_ck)
            if session:
                self.session = Session(session)
        if not hasattr(self, 'session'):
            self.session = Session(salt=self.request.headers)
            model.Session.put(self.session['id'], self.session)
        self.set_secure_cookie('session', self.session['id'], expires_days=self.session_expiry)
        self.tmpl['session'] = self.session

    def session_end(self):
        self.clear_cookie('session')
        self.clear_cookie('auth')
        model.Session.delete(self.session['id'])

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

    def finish(self, chunk=None):
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

class Index(RequestHandler):
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


class Logout(RequestHandler):
    def get(self):
        self.auth_end()
        self.session_end()
        self.redirect('/')

    def post(self):
        self.auth_end()
        self.session_end()
        self.redirect('/')



# Main
def main():
    define("port", default=options.port, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    app = Application()
    app.setup_handlers()
    #tornado.locale.load_translations(
    #  os.path.join(os.path.dirname(__file__), "translations"))

if __name__ == "__main__":
    main()
