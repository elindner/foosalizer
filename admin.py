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

import models


class Admin(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    matches = models.Match.all().order('kickoff').fetch(1000)
    players = models.Player.all().order('nickname').fetch(1000)
    data = {
      'user': user,
      'matches': matches,
      'players': players,
    }
    path = os.path.join(os.path.dirname(__file__), 'templates', 'admin.html')
    self.response.out.write(template.render(path, data))


class DeleteMatch(webapp.RequestHandler):
  def post(self):
    match_keys = self.request.get('match', allow_multiple=True)
    for match_key in match_keys:
      match = models.Match.get(match_key)
      players = match.players
      query = models.Goal.all()
      query.filter('match =', match)
      goals = query.fetch(1000)
      db.delete(goals)
      db.delete(match)
      for player in players:
        models.PlayerStats.rebuild_for_player(models.Player.by_nickname(player))
        
    self.redirect(Admin.get_url())


class RebuildStats(webapp.RequestHandler):
  def get(self, player_key):
    players = []
    if player_key == 'all':
      players = models.Player.all().fetch(1000)
    else:
      players = [models.Player.get(player_key)]

    for player in players:
      models.PlayerStats.rebuild_for_player(player)

    self.redirect(Admin.get_url())


def main():
  handlers = [
    ('/admin', Admin),
    ('/admin/delete', DeleteMatch),
    ('/admin/rebuild_stats/(.*)', RebuildStats),
  ]
  application = webapp.WSGIApplication(handlers, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
