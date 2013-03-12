# Generic config system to be extended by applications
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Python Imports
import logging as log
import os

# Extern Imports
import tornado.options
from tornado.options import define, options

define("smtp_host", default=None, help="SMTP host to connect", type=str)
define("smtp_port", default=None, help="SMTP port to connect", type=str)
define("smtp_user", default=None, help="SMTP user to connect", type=str)
define("smtp_pass", default=None, help="SMTP pass to connect", type=str)
define("use_sessions", default=True, help="Use sessions", type=bool)
define("use_auth", default=True, help="Use member authentication", type=bool)
define("session_expiry", default=90, help="Session expiration in days", type=int)
define("auth_expiry", default=90, help="Authentication expiration in days", type=int)


def get_env():
    if options.get('env'):
        return options.env
    else:
        return os.getenv('HYDRA_ENV')

# Allow projects to override tornado options
def set_env(environments):
    env_options = environments.get(get_env(), {})
    for setting, value in env_options.items():
        if options.get(setting):
            options[setting].set(value)
