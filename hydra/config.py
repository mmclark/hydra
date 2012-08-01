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
from tornado.options import options

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
