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

import models

import analyser
import gviz_api


class FoosalizerHandler(webapp.RequestHandler):
  def GetPlayer(self):
    user = users.get_current_user()
    player = models.Player.by_nickname(user.nickname())
    if not player:
      logging.info('User %s not registered, registering now' % user.nickname())
      player = models.Player(nickname=user.nickname())
      player.put()
    return player

  def Render(self, template_name, data):
    path = os.path.join(os.path.dirname(__file__), 'templates', template_name)
    self.response.out.write(template.render(path, data))


class Index(FoosalizerHandler):
  def get(self, show_all_matches=False):
    player = self.GetPlayer()
    show_all_matches = self.request.get('show_all_matches')

    query = models.Match.all()
    query.filter('players =', player.nickname).order('-kickoff')
    if show_all_matches:
      matches = query.fetch(1000)
    else:
      matches = query.fetch(3)

    history = models.PlayerStats.by_player(player, order='-date', limit=10)

    current_stats = {}
    if history: 
      current_stats = history[0]

    charts = {}
    for player_stats in history:
      for key in ['awesomeness', 'pwnability', 'lethality']:
        charts.setdefault(key, []).insert(0, getattr(player_stats, key))

    data = {
      'player': player,
      'matches': matches,
      'history': history,
      'charts': charts,
      'current_stats': current_stats,
      'logout_url': users.create_logout_url('/'),
    }

    self.Render('index.html', data)


class NewMatch(FoosalizerHandler):
  def get(self):
    query = models.Player.all()
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
    match = models.Match(creator=player.nickname,
                         kickoff=kickoff,
                         players=data['players'])
    match_key = match.put()

    for goal_data in data['goals']:
      goal = models.Goal(time=goal_data['time'] / 1000,
                         match=match_key,
                         player=goal_data['player'],
                         team=goal_data['team'],
                         position=goal_data['position'],
                         team_mate=goal_data['team_mate'],
                         opponent_back=goal_data['opponent_back'],
                         opponent_front=goal_data['opponent_front'])
      goal.put()

    for nickname in data['players']:
      match_player = models.Player.by_nickname(nickname)
      # models.PlayerStats.rebuild_for_player(match_player)
      models.PlayerStats.update_for_player_and_match(match_player, match)

    self.redirect(Results.get_url(match_key))


class Results(FoosalizerHandler):
  def get(self, match_key):
    match = models.Match.get(db.Key(match_key))    
    goals = models.Goal.by_match(match, order='time')
    data = {
      'match': match,
      'goals': goals,
    }
    self.Render('results.html', data)


class MatchAnalysis(FoosalizerHandler):
  def get(self, match_key):
    self.Render('match_analysis.html', {'match_key': match_key})


class PlayerAnalysis(FoosalizerHandler):
  def get(self, player):
    query = models.Goal.all()
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


class Charts(FoosalizerHandler):
  def get(self):
    stats = models.PlayerStats.all_players_latest()

    keys = (
      ('awesomeness',  ('number', 'Awesomeness')),
      ('matches_played', ('number', 'Matches')),
      ('goals_scored', ('number', 'Scored')),
      ('lethality',  ('number', 'Lethality')),
      ('goals_conceded',  ('number', 'Conceded')),
      ('pwnability',  ('number', 'Pwnability')),
    )

    description = dict(keys)

    data = []
    for player, stat in stats.iteritems():
      if stat and stat.matches_played > 0:
        datum = {'player': player}
        for key in description:
          datum[key] = getattr(stat, key, 0)
        data.append(datum)

    order = ['player']
    order.extend([key[0] for key in keys])
    description['player'] = ('string', 'Player')

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)
    json = data_table.ToJSon(columns_order=order, order_by='awesomeness')

    self.Render('charts.html', {'json': json})


def main():
  handlers = [
    ('/', Index),
    ('/analysis/match/(\w+)', MatchAnalysis),
    ('/analysis/player/(\w+)', PlayerAnalysis),
    ('/charts', Charts),
    ('/results/(\w+)', Results),
    ('/newmatch', NewMatch),
    ('/savematch', SaveMatch),
  ]
  application = webapp.WSGIApplication(handlers, debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
