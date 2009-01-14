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
    logging.info(self.player + '/' + str(self.match_key) + ':' + str(self.count))
    self.data.setdefault(self.player, 1)
    if self.data[self.player] < self.count:
      logging.info('@')
      self.data[self.player] = self.count
    self.count = 1

  def Collect(self, goal):
    if self.player is None:
      self.player = goal.player

    if self.match_key is None:
      self.match_key = goal.match.key()

    logging.info(self.match_key)
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
