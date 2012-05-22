# E-mail utilities
#
# Copyright 2012 Michael D'Agosta <mdagosta@codebug.com>
#
# This program is copyrighted Free Software, and may be used under the
# terms of the Python License.


# Python Imports
import logging as log
import os.path
import email.mime.text
import email.mime.multipart
import email.Utils
import email.Header
import smtplib
import traceback

# Extern Imports
import tornado.template
from tornado.options import options

# Project Imports
import stdlib
import config


# A lot is adapted from http://mg.pov.lt/blog/unicode-emails-in-python

def mime(txt, subtype):
    if txt is None:
        return None
    for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
        try:
            txt.encode(body_charset)
        except UnicodeError:
            pass
        else:
            break
    charset = body_charset
    if charset == 'UTF-8':
        txt = stdlib._unicode(txt, charset)
    return email.mime.text.MIMEText(txt.encode(charset), subtype, charset)

def encode_email(sender, recipient, subject, body, reply_to, service_sender):
    plain, html = None, None
    if isinstance(body, basestring):
        plain = body
    else:
        plain = body.get('plain', None)
        html = body.get('html', None)
    header_charset = 'ISO-8859-1'
    parts = []
    if plain:
        parts.append(mime(plain, 'plain'))
    if html:
        parts.append(mime(html, 'html'))
    if len(parts) > 1:
        msg = email.mime.multipart.MIMEMultipart('alternative')
        for p in parts:
            msg.attach(p)
    else:
        msg = parts[0]
    # Set up headers
    headers = (('To', recipient), ('From', sender), ('Reply-to', reply_to),
               ('Sender', service_sender))
    for header in headers:
        if not header[1]:
            continue
        name, addr = email.Utils.parseaddr(header[1])
        name = str(email.Header.Header(unicode(name), header_charset))
        addr = addr.encode('ascii')
        if header[0] == 'To' and name:
            msg[header[0]] = '"%s" <%s>' % (name.replace('"', "'"), addr)
        else:
            msg[header[0]] = email.Utils.formataddr((name, addr))
    # Finish message
    subject = stdlib._unicode(subject, header_charset)
    msg['Subject'] = email.Header.Header(unicode(subject), header_charset)
    return msg.as_string()

def render_email(handler, from_email, to_addrs, subject, template, email_opts, **kwargs):
    if not handler:
        template_path = os.path.join(os.path.dirname(__file__), "templates")
        template_loader = tornado.template.Loader(template_path)
        plain = stdlib._unicode(template_loader.load(template+'.txt').generate(**email_opts))
        html = stdlib._unicode(template_loader.load(template+'.html').generate(**email_opts))
    else:
        plain = handler.render_string('%s.txt' % template, **email_opts)
        html =  handler.render_string('%s.html' % template, **email_opts)
    body = {'plain': plain, 'html': html}
    reply_to = kwargs.get('reply_to', from_email)
    service_sender = kwargs.get('service_sender', from_email)
    return encode_email(from_email, to_addrs, subject, body, reply_to, service_sender)

def sendmail(from_addr, to_addrs, msg):
    try:
        conn = smtplib.SMTP('localhost')
        conn.sendmail(from_addr, to_addrs, msg)
        return conn.quit()
    except:
        traceback.print_exc()

def error_email(domain, handler):
    service_email = options.from_email
    email = options.to_email
    subject = "Hydra Error on %s" % domain
    tb = traceback.format_exc()
    tmpl = {'email': email, 'domain': domain, 'handler': handler, 'traceback': tb}
    email_msg = render_email(None, service_email, email, subject, 'error_email', tmpl)
    sendmail(service_email, email, email_msg)
