#!/usr/bin/env python
#
# Hydra Daemon
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Environment
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
import tornado.options; from tornado.options import options
import tornado.escape
import tornado.web
import django.conf; django.conf.settings.configure()    # Disable django settings
import django.forms.fields

# Project Imports
import uimethods
import database
import stdlib
import mail
import model


# Application
class Application(tornado.web.Application):
    def __init__(self, **kwargs):
        settings = dict(
          cookie_secret=options.cookie_secret,
          xsrf_cookies=True,
          debug=options.debug,
          login_url='/',
          ui_methods=[uimethods],
        )
        settings.update(kwargs)
        if 'template_path' in options:
            settings['template_path'] = options.template_path
        if 'static_path' in options:
            settings['static_path'] = options.static_path
        tornado.web.Application.__init__(self, **settings)

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
        self.tmpl = {}
        self.tmpl['domain'] = options.domain
        self.tmpl['app_name'] = options.app_name
        self.tmpl['user_agent'] = self.request.headers.get('User-Agent')
        self.tmpl['scheme'] = 'https://'

    def logw(self, var, msg=''):
        log.warning('%s %s %s', msg, type(var), pprint.pformat(var))

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
            mail.error_email(options.domain, self)
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
        self.set_secure_cookie('session', self.session['id'], expires_days=options.session_expiry)
        self.tmpl['session'] = self.session

    def session_end(self):
        self.clear_cookie('session')
        self.clear_cookie('auth')
        model.Session.delete(self.session['id'])

    def set_options_cookie(self, opts):
        self.set_secure_cookie('options', self.cookie_encode(opts), expires_days=365)

    def get_options_cookie(self):
        return self.cookie_decode(self.get_secure_cookie('options'))

    def validate_form(self, form_fields=None):
        self.tmpl['validated'] = True
        form_fields = form_fields or getattr(self, 'form_fields')
        for name, field in form_fields.items():
            field['value'] = self.get_argument(name, None)
            try:
                field['cleaned'] = field.clean(field['value'])
                field['valid'] = True
            except django.forms.fields.ValidationError, ex:
                field['valid'] = False
                field['error_msg'] = ex.messages[0]
        self.form_valid = False not in [v['valid'] for f, v in form_fields.items()]
        return self.form_valid

    def prepare(self):
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Pragma', 'no-cache')
        self.set_header('Expires', 'Sat, 10 Jun 2006 03:08:13 GMT')
        self.page_name = '%s.%s' % (self.__class__.__name__, self.request.method)
        self.tmpl['page_name'] = self.page_name
        self.request.args = {}
        for key, value in self.request.arguments.iteritems():
            self.request.args[key] = value[0]
        if options.use_sessions:
            self.session_start()

    def finish(self, chunk=None):
        if options.use_sessions and hasattr(self, 'session') and self.session.dirty():
            model.Session.put(self.session['id'], self.session)
        tornado.web.RequestHandler.finish(self, chunk)

    def head(self):
        pass


class EmailField(django.forms.fields.EmailField, dict):
    pass

class DateField(django.forms.fields.DateField, dict):
    pass

class CharField(django.forms.fields.CharField, dict):
    pass

class IntegerField(django.forms.fields.IntegerField, dict):
    pass

class DecimalField(django.forms.fields.DecimalField, dict):
    pass


# Main
def main():
    define("port", default=options.port, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    app = Application()
    app.setup_handlers()

if __name__ == "__main__":
    main()
