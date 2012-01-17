#!/usr/bin/python
#
# Hello World on Hydra
#
# Copyright 2012 Michael D'Agosta

import log
import tornado.web
import hydra

class HelloWorld(hydra.Hydra):
  def get(self):
    self.session_start()
    self.render("templates/index.html")

handler_urls = [
  (r'/', HelloWorld),
  (r'/(favicon.ico)$', tornado.web.StaticFileHandler, {"path": "helloworld/static"}),
  (r'/(robots.txt)$', tornado.web.StaticFileHandler, {"path": "helloworld/static"}),
  (r'/static/(.*)', tornado.web.StaticFileHandler, {"path": "helloworld/static"}),
  ]
