#!/usr/bin/env python

import logging
from google.appengine.ext import db
from models import Goal


class Analyser(object):
  def __init__(self):
    self.name = self.__class__.__name__
    self.data = {}

  def Collect(self, goal, previous_goal, next_goal):
    raise NotImplemented

  def GetDescription(self):
    raise NotImplemented

  def GetData(self):
    raise NotImplemented


class GoalsByPosition(Analyser):
  def Collect(self, goal, next, previous):
    self.data.setdefault(goal.player, {'front': 0, 'back': 0})
    self.data[goal.player].setdefault(goal.position, 0)
    self.data[goal.player][goal.position] += 1


class TotalGoals(Analyser):
  def Collect(self, goal, next, previous):
    self.data.setdefault(goal.player, 0)
    self.data[goal.player] += 1

  def GetMetadata(self):
    return {
      'player': ('string', 'Player'),
      'goals': ('number', 'Goals')
    }

  def GetData(self):
    return [{'player': d, 'goals': self.data[d]} for d in self.data]


class Pwned(Analyser):
  def Collect(self, goal, next, previous):
    self.data.setdefault(goal.player, {})
    self.data[goal.player].setdefault(goal.opponent_back, 0)
    self.data[goal.player][goal.opponent_back] += 1


class PwnedBy(Analyser):
  # TODO(edgard): this could be inferred by Pwned.
  def Collect(self, goal, next, previous):
    self.data.setdefault(goal.opponent_back, {})
    self.data[goal.opponent_back].setdefault(goal.player, 0)
    self.data[goal.opponent_back][goal.player] += 1


def Analyse(goals, analysers_classes):
  analysers = [analyser_class() for analyser_class in analysers_classes]
  for i in xrange(len(goals)):
    previous = None
    next = None
    if i > 0: previous = goals[i - 1]
    if i < len(goals) - 1: next = goals[i + 1]

    for analyser in analysers:
      analyser.Collect(goals[i], previous, next)

  results = {}
  for analyser in analysers:
    results[analyser.name] = {
      'metadata': analyser.GetMetadata(),
      'data': analyser.GetData()
    }

  return results
