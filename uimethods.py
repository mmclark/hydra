import log

def get_member_id(handler):
  return handler.session.get('member_id', None)

def get_current_user(handler):
  # XXX need a way to use different authentication methods here
  if hasattr(handler, 'session') and handler.session:
    auth_key = handler.tmpl.get('auth_key', 'username')
    username = handler.session.get(auth_key, None)
    if not username:
      return None
    if len(username) > 23:
      username = username[:21] + '...'
    return username

def mobile(handler):
  agent = handler.tmpl.get('user_agent', None)
  if not agent:
    return None
  agent = agent.lower()
  return ('iphone' in agent or 'android' in agent or 'blackberry' in agent)

def acl_write(handler):
  return get_current_user(handler) == 'mdagosta'

def isodate_to_english(handler, isodate):
  return "%s-%s-%s" % (isodate[:4], isodate[4:6], isodate[6:8])
