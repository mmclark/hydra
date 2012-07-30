# Standard library / utilities
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

# Python Imports
import hashlib
import inspect
import os
import re
import sys
import time
import traceback
import xml.sax.saxutils

 # Extern Imports
import bcrypt


def md5hex(val):
    return hashlib.md5(val).hexdigest()

BCRYPT_LOG_ROUNDS = 10

def bcrypt_salt(log_rounds=8):
    return bcrypt.gensalt(log_rounds=log_rounds)

def bcrypt_hashpw(password, log_rounds):
    return bcrypt.hashpw(password, log_rounds)

def bcrypt_password(password):
    return bcrypt.hashpw(password, bcrypt.gensalt(log_rounds=BCRYPT_LOG_ROUNDS))

def _unicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj

def html_unescape(val):
    return xml.sax.saxutils.unescape(val, {'&quot;': '"'})

def get_request_handler():    #  This function is very slow
    f = inspect.currentframe()
    while (f):
        info = inspect.getframeinfo(f)
        if inspect.getmodulename(info[0]) == 'web' and info[2] == '_execute':
            reqh = f.f_locals['self']
            return reqh
        f = f.f_back

def absdir(path):
    return os.path.abspath(os.path.dirname(path))


# Make it easier to use ansi escape sequences for terminal colors
colors = {'black' : 30, 'red' : 31, 'green' : 32, 'yellow' : 33, 'blue' : 34,
          'magenta' : 35, 'cyan' : 36, 'white' : 37, 'reset': 39, }
attrs = {'reset':'0', 'bold':'1', 'faint':'2', 'regular':'2',
         'underscore':'4', 'blink':'5', 'reverse':'7'}

def ansi_esc(colorName, **kwargs):
    out = '\x1B['
    if 'attr' in kwargs and kwargs['attr'] in attrs:
        out += attrs[kwargs['attr']] + ';'
    if 'bgcolor' in kwargs and kwargs['bgcolor'] in colors:
        bgcolor = colors[kwargs['bgcolor']] + 10
        out += str(bgcolor) + ';'
    out += str(colors[colorName]) + 'm'
    return out

def cline(line):
    pick_ansi = {'-': 'red', '+': 'green', '*': 'green'}
    color = pick_ansi.get(line[0], '')
    if color != '':
        print ansi_esc(color) + line + ansi_esc('reset')
    else:
        print line

def cdiff(line):
    pick_ansi = {'-': 'red', '+': 'green', '*': 'green'}
    color = pick_ansi.get(line[0], '')
    if color != '':
        return ansi_esc(color) + line + ansi_esc('reset')
    else:
        return line

def cstr(data, color):
    return ansi_esc(color) + data + ansi_esc('reset')

# conceal() and reveal() are an attempt to mitigate the failure of most unixes
# to support the conceal and reveal ansi escape sequences 8 and 28
def conceal():
    print ansi_esc('black', bgcolor='black'),
    print >> sys.stderr, ansi_esc('black', bgcolor='black'),

def reveal():
    print ansi_esc('reset', bgcolor='reset', attr='reset'),
    print >> sys.stderr, ansi_esc('reset', bgcolor='reset', attr='reset'),
