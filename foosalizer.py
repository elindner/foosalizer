#!/usr/bin/env python

import time
import datetime
import logging
import os
import simplejson
import urllib
import wsgiref.handlers

import pygooglechart

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Goal
from models import Match
from models import Player

import analyser


class FoosalizerHandler(webapp.RequestHandler):
  def GetPlayer(self):
    user = users.get_current_user()
    query = Player.all()
    query.filter('nickname =', user.nickname())
    player = query.get()
    if not player:
      logging.info('User %s not registered, registering now' % user.nickname())
      player = Player(nickname=user.nickname())
      player.put()
    return player

  def Render(self, template_name, data):
    path = os.path.join(os.path.dirname(__file__), 'templates', template_name)
    self.response.out.write(template.render(path, data))


class IndexHandler(FoosalizerHandler):
  def get(self):
    player = self.GetPlayer()
    query = Match.all()
    query.filter('players =', player.nickname).order('kickoff')
    matches = query.fetch(1000)

    data = {
      'player': player,
      'matches': matches,
      'logout_url': users.create_logout_url('/'),
    }
    self.Render('index.html', data)


class MatchHandler(FoosalizerHandler):
  def get(self):
    query = Player.all()
    players = query.fetch(1000) # how many?
    data = {
      'players': [player.nickname for player in players]
    }
    self.Render('match.html', data)


class SaveMatchHandler(FoosalizerHandler):
  def post(self):
    player = self.GetPlayer()
    data = simplejson.loads(self.request.get('json_data'))
    kickoff = datetime.datetime.fromtimestamp(data['kickoff'] / 1000)
    match = Match(creator=player.nickname,
                  kickoff=kickoff,
                  players=data['players'])
    match_key = match.put()

    for goal_data in data['goals']:
      goal = Goal(time=goal_data['time'] / 1000,
                  match=match_key,
                  player=goal_data['player'],
                  team=goal_data['team'],
                  position=goal_data['position'],
                  team_mate=goal_data['team_mate'],
                  opponent_back=goal_data['opponent_back'],
                  opponent_front=goal_data['opponent_front'])
      goal.put()

    self.redirect('/results?match=%s' % match_key)


class ResultsHandler(FoosalizerHandler):
  def get(self):
    match_key = db.Key(self.request.get('match'))
    match = Match.get(match_key)
    query = Goal.all()
    query.filter('match =', match_key).order('time')
    goals = query.fetch(1000) # how many?
    data = {
      'match': match,
      'goals': goals,
    }
    self.Render('results.html', data)


class AnalysisHandler(FoosalizerHandler):
  def get(self):
    match_key = self.request.get('match')
    player = self.request.get('player')

    match = None
    query = Goal.all()
    if match_key != '':
      match = Match.get(db.Key(match_key))
      query.filter('match =', match)

    if player != '':
      if player != 'all':
        query.filter('player =', player)

    goals = query.fetch(1000) # how many?

    stats = []
    for name, analysis in analyser.Analyse(goals).iteritems():
      pies = {'name': name, 'urls': []}
      for player, data in analysis.iteritems():
        pie = pygooglechart.PieChart3D(250, 100)
        pie.set_pie_labels(data[0])
        pie.add_data(data[1])
        pie.set_legend([str(x) for x in data[1]])
        pie.set_title(player)
        pies['urls'].append(pie.get_url())

      stats.append(pies)

    data = {
      'match': match,
      'goals': goals,
      'stats': stats,
      'player': player
    }

    self.Render('analysis.html', data)


def main():
  handlers = [
    ('/', IndexHandler),
    ('/analysis', AnalysisHandler),
    ('/results', ResultsHandler),
    ('/match', MatchHandler),
    ('/savematch', SaveMatchHandler),
  ]
  application = webapp.WSGIApplication(handlers, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
