# Standard library / utilities
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

import hashlib, re, smtplib, sys, time, traceback, xml.sax.saxutils
import bcrypt

BCRYPT_LOG_ROUNDS = 10

def md5hex(val):
  return hashlib.md5(val).hexdigest()

def bcrypt_salt():
  return bcrypt.gensalt(log_rounds=8)

def bcrypt_password(password):
    return bcrypt.hashpw(password, bcrypt.gensalt(log_rounds=BCRYPT_LOG_ROUNDS))

def _unicode(obj, encoding='utf-8'):
  if isinstance(obj, basestring):
    if not isinstance(obj, unicode):
      obj = unicode(obj, encoding)
  return obj

def html_unescape(val):
  return xml.sax.saxutils.unescape(val, {'&quot;': '"'})

def _html_entity_callback(matches):
    entity_id = matches.group(1)
    try:
        return unichr(int(entity_id))
    except:
        return entity_id

def html_entity_decode(val):
  return re.sub("&#(\d+)(;|(?=\s))", _html_entity_callback, val)


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


# Sessions
# From: http://stackoverflow.com/questions/2060972/subclassing-python-dictionary-to-override-setitem
class Session(dict):
  def __init__(self, *args, **kwargs):
    self.update(*args, **kwargs)
    if kwargs.get('salt') and not kwargs.get('id'):
      self['id'] = md5hex('%10.13f %s' % (time.time(), kwargs['salt']))
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
