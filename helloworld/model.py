# Hello World sample data model
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.

import log, model, stdlib, topology
import hydra

def db_exec(query, *args, **kwargs):
  return hydra.model.db_exec(query, *args, schema='helloworld', **kwargs)

def db_get(query, *args, **kwargs):
  return hydra.model.db_get(query, *args, schema='helloworld', **kwargs)

def db_iter(query, *args, **kwargs):
  return hydra.model.db_iter(query, *args, schema='helloworld', **kwargs)

def db_query(query, *args, **kwargs):
  return hydra.model.db_query(query, *args, schema='helloworld', **kwargs)


def get_session(session_md5):
  sess = db_get('SELECT * FROM session WHERE session_md5=%s', session_md5)
