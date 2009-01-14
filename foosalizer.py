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


class Index(FoosalizerHandler):
  def get(self):
    player = self.GetPlayer()
    show_all_matches = self.request.get('show_all_matches')

    query = Match.all()
    query.filter('players =', player.nickname).order('-kickoff')
    if show_all_matches:
      matches = query.fetch(1000)
    else:
      matches = query.fetch(3)
    stats = analyser.AnalyseHighLevel(player.nickname)

    if len(matches):
      logging.info(matches[0].to_xml())

    data = {
      'player': player,
      'matches': matches,
      'stats': stats,
      'logout_url': users.create_logout_url('/'),
    }
    self.Render('index.html', data)


class NewMatch(FoosalizerHandler):
  def get(self):
    query = Player.all()
    players = query.fetch(1000) # how many?
    data = {
      'players': [player.nickname for player in players]
    }
    self.Render('match.html', data)


class SaveMatch(FoosalizerHandler):
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

    self.redirect(Results.get_url(match_key))


class Results(FoosalizerHandler):
  def get(self, match_key):
    match = Match.get(db.Key(match_key))
    query = Goal.all()
    query.filter('match =', match.key()).order('time')
    goals = query.fetch(1000)  # how many?
    data = {
      'match': match,
      'goals': goals,
    }
    self.Render('results.html', data)


class MatchAnalysis(FoosalizerHandler):
  def get(self, match_key):
    match = Match.get(db.Key(match_key))
    goals = Goal.all().filter('match =', match).fetch(1000) # how many?

    stats = []
    for name, analysis in analyser.Analyse(goals).iteritems():
      pies = {'name': name, 'urls': []}
      for player, data in analysis.iteritems():
        pie = pygooglechart.PieChart3D(250, 100)
        pie.set_pie_labels(str(data[1]))
        pie.add_data(data[1])
        pie.set_legend([str(x) for x in data[0]])
        pie.set_title(player)
        pies['urls'].append(pie.get_url())

      stats.append(pies)

    data = {
      'match': match,
      'goals': goals,
      'stats': stats,
    }

    self.Render('match_analysis.html', data)


class PlayerAnalysis(FoosalizerHandler):
  def get(self, player):
    query = Goal.all()
    if player != 'all':
      query.filter('player =', player)
    query.fetch(1000)

    stats = []
    for name, analysis in analyser.Analyse(goals).iteritems():
      pies = {'name': name, 'urls': []}
      for player, data in analysis.iteritems():
        pie = pygooglechart.PieChart3D(250, 100)
        pie.set_pie_labels(str(data[1]))
        pie.add_data(data[1])
        pie.set_legend([str(x) for x in data[0]])
        pie.set_title(player)
        pies['urls'].append(pie.get_url())

      stats.append(pies)

    data = {
      'goals': goals,
      'stats': stats,
      'player': player
    }

    self.Render('player_analysis.html', data)


def main():
  handlers = [
    ('/', Index),
    ('/analysis/match/(\w+)', MatchAnalysis),
    ('/analysis/player/(\w+)', PlayerAnalysis),
    ('/results/(\w+)', Results),
    ('/newmatch', NewMatch),
    ('/savematch', SaveMatch),
  ]
  application = webapp.WSGIApplication(handlers, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
