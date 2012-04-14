# Generic config system to be extended by applications
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Python Imports
import logging as log
import os
env = os.getenv('HYDRA_ENV')

# Extern Imports
import tornado.options


# Allow projects to override tornado options
def set_env(environments):
    env_options = environments.get(env, {})
    for setting, value in env_options.items():
        if tornado.options.options.get(setting):
            tornado.options.options[setting].set(value)
