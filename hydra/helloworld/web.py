# Hello World on Hydra
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

import log
import tornado.web
import hydra
import model

class HelloWorld(hydra.Hydra):
  def get(self):
    self.session_start()
    model.get_session(self.session['id'])
    self.render("templates/index.html")

handler_urls = [
  (r'/', HelloWorld),
  (r'/(favicon.ico)$', tornado.web.StaticFileHandler, {"path": "helloworld/static"}),
  (r'/(robots.txt)$', tornado.web.StaticFileHandler, {"path": "helloworld/static"}),
  (r'/static/(.*)', tornado.web.StaticFileHandler, {"path": "helloworld/static"}),
  ]
