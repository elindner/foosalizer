#!/usr/bin/env python

import logging
from google.appengine.ext import db
from models import Goal


class Analyser(object):
  def __init__(self):
    self.name = self.__class__.__name__
    self.data = {}

  def GetResults(self):
    result = {}
    for player, data in self.data.iteritems():
      result[player] = (tuple(data.keys()), tuple(data.values()))
    return result


class GoalsByPosition(Analyser):
  def Collect(self, goal):
    self.data.setdefault(goal.player, {'front': 0, 'back': 0})
    self.data[goal.player].setdefault(goal.position, 0)
    self.data[goal.player][goal.position] += 1


class Pwned(Analyser):
  def Collect(self, goal):
    self.data.setdefault(goal.player, {})
    self.data[goal.player].setdefault(goal.opponent_back, 0)
    self.data[goal.player][goal.opponent_back] += 1


class FastestGoal(Analyser):
  def Collect(self, goal):
    self.data.setdefault(goal.player, []).append(goal.time)

  def GetResults(self):
    results = {}
    for player in self.data:
      results[player] = int(min(self.data[player]))
    return results


class PwnedBy(Analyser):
  def Collect(self, goal):
    self.data.setdefault(goal.opponent_back, {})
    self.data[goal.opponent_back].setdefault(goal.player, 0)
    self.data[goal.opponent_back][goal.player] += 1


class TotalGoals(Analyser):
  def Collect(self, goal):
    self.data.setdefault(goal.player, 0)
    self.data[goal.player] += 1

  def GetResults(self):
    result = {}
    result[''] = (tuple(self.data.keys()), tuple(self.data.values()))
    return result


class GoalsInARow(Analyser):
  # TODO(edgard): this one makes no sense when called with player=...
  # we should consider match/date?

  def __init__(self):
    Analyser.__init__(self)
    self.player = None
    self.count = 0
    self.match_key = None

  def MaybeUpdatePlayerCount(self):
    logging.debug('%s/%s:%s' % (self.player, self.match_key, self.count))
    self.data.setdefault(self.player, 1)
    if self.data[self.player] < self.count:
      self.data[self.player] = self.count
    self.count = 1

  def Collect(self, goal):
    if self.player is None:
      self.player = goal.player

    if self.match_key is None:
      self.match_key = goal.match.key()

    if self.player != goal.player or self.match_key != goal.match.key():
      self.MaybeUpdatePlayerCount()
    else:
      self.count += 1

    self.player = goal.player
    self.match_key = goal.match.key()

  def GetResults(self):
    self.MaybeUpdatePlayerCount()
    result = {}
    result[''] = (tuple(self.data.keys()), tuple(self.data.values()))
    return result



def Analyse(goals):
  analysers = [
      GoalsByPosition(),
      Pwned(),
      PwnedBy(),
      TotalGoals(),
      GoalsInARow(),
  ]
  analysis = {}

  for goal in goals:
    for analyser in analysers:
      analyser.Collect(goal)

  for analyser in analysers:
    analysis[analyser.name] = analyser.GetResults()

  return analysis


def AnalyseHighLevel(nickname):
  stat_values = {}
  # TODO(damien): These queries will need to be split up when results > 1000.
  # TODO(damien): Split into goals for/against.
  query = Goal.all().order('time')
  goals = query.fetch(1000)

  def goals_scored():
    analyser = TotalGoals()
    for goal in goals:
      analyser.Collect(goal)
    try:
      return analyser.GetResults()[''][1][0]
    except IndexError:
      return 0

  def goals_conceded():
    analyser = PwnedBy()
    for goal in goals:
      analyser.Collect(goal)
    raw = analyser.GetResults().get(nickname, None)
    if raw:
      return sum([goal_record[1] for goal_record in zip(raw[0], raw[1])])
    else:
      return 0

  def fastest_goal():
    analyser = FastestGoal()
    for goal in goals:
      analyser.Collect(goal)
    return analyser.GetResults().get(nickname, 'n/a')

  def goals_in_a_row():
    analyser = GoalsInARow()
    for goal in goals:
      analyser.Collect(goal)
    try:
      return analyser.GetResults()[''][1][0]
    except IndexError:
      return 0

  def nemesis():
    nemesis = {'player': '', 'goals': 0}
    analyser = PwnedBy()
    for goal in goals:
      analyser.Collect(goal)
    raw = analyser.GetResults().get(nickname, None)
    if raw:
      pwners = dict(zip(raw[0], raw[1]))
      for player, goal_count in pwners.items():
        if goal_count > nemesis['goals']:
          nemesis['player'] = player
          nemesis['goals'] = goal_count
    return nemesis

  stat_functions = {
      'goals_scored': goals_scored,
      'fastest_goal': fastest_goal,
      'goals_in_a_row': goals_in_a_row,
      'nemesis': nemesis,
      'goals_conceded': goals_conceded,
  }

  for name, fn in stat_functions.items():
    stat_values[name] = fn()

  return stat_values
