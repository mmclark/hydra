# Hello World sample config file
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

import os
from tornado.options import define, options
import hydra.stdlib
import hydra.config

# Application defaults
define("host", default=None, help="Host to bind", type=str)
define("port", default=8888, help="Port to bind", type=int)
define('mysql_host', default='localhost')
define('mysql_schema', default='helloworld')
define('mysql_user', default='helloworld')
define('mysql_password', default='HI!!')
define('basedir', default=hydra.stdlib.absdir(__file__))

# Environment settings
environments = {
    'quartz': {
        'from_email': 'mdagosta@codebug.com',
        'to_email': 'mdagosta@codebug.com',
    }
}
hydra.config.set_env(environments)
