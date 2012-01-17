#!/usr/bin/env python
#
# Hydra Daemon
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Environment
if __name__ == '__main__':
  import logging, tornado.options   # Configure logging first so works in imports
  from tornado.options import define, options
  if options.logging != 'none':
    logging.getLogger().setLevel(getattr(logging, options.logging.upper()))
    tornado.options.enable_pretty_logging()
import os
env = os.getenv('HYDRA_ENV')


# Imports
import pprint
import tornado.httpserver, tornado.ioloop, tornado.options, tornado.web
import hydra, topology, uimethods
import helloworld.handlers


# Application
class Application(tornado.web.Application):
  def __init__(self):
    settings = dict(
      cookie_secret="9a8sd7f;23,.542.3,4--hydra--12341234/>!!|=-",
      xsrf_cookies=True,
      #template_path=os.path.join(os.path.dirname(__file__), "templates"),
      #static_path=os.path.join(os.path.dirname(__file__), "static"),
      debug=True,
      login_url='/',
      ui_methods=[uimethods],
    )
    tornado.web.Application.__init__(self, **settings)

  def setup_handlers(self):
    self.add_handlers(r".*helloworld\.com", helloworld.handlers.handler_urls)


# Main
def main():
  _host = topology.environments[env]['host']
  _port =  topology.environments[env]['port']
  define("port", default=_port, help="run on the given port", type=int)
  tornado.options.parse_command_line()
  app = Application()
  app.setup_handlers()
  #tornado.locale.load_translations(
  #  os.path.join(os.path.dirname(__file__), "translations"))
  http_server = tornado.httpserver.HTTPServer(app, xheaders=True, no_keep_alive=True)
  logging.info('listening on %s:%s' % (_host, options.port))
  http_server.listen(options.port, address=_host)
  tornado.ioloop.IOLoop.instance().start()
if __name__ == "__main__":
  main()
