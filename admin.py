#!/usr/bin/env python

import time
import datetime
import logging
import os
import simplejson
import urllib
import wsgiref.handlers

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Goal
from models import Match
from models import Player


class AdminHandler(webapp.RequestHandler):
  def get(self):
    query = Match.all()
    matches = query.order('kickoff').fetch(1000)
    user = users.get_current_user()

    data = {
      'user': user,
      'matches': matches,
    }
    path = os.path.join(os.path.dirname(__file__), 'templates', 'admin.html')
    self.response.out.write(template.render(path, data))


class DeleteMatchHandler(webapp.RequestHandler):
  def post(self):
    match_keys = self.request.get('match', allow_multiple=True)
    for match_key in match_keys:
      match = Match.get(match_key)
      query = Goal.all()
      query.filter('match =', match)
      goals = query.fetch(1000)
      db.delete(goals)
      db.delete(match)
    self.redirect('/admin')


def main():
  handlers = [
    ('/admin', AdminHandler),
    ('/admin/delete', DeleteMatchHandler),
  ]
  application = webapp.WSGIApplication(handlers, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
