#!/usr/bin/env python

from google.appengine.ext import db


class Player(db.Model):
  # Should I use UserProperty? Why?
  nickname = db.StringProperty(required=True)

  @classmethod
  def by_nickname(cls, nickname):
    return cls.all().filter('nickname =', nickname).get()


class Match(db.Model):
  creator = db.StringProperty(required=True)
  kickoff = db.DateTimeProperty(required=True)
  players = db.StringListProperty()

  @classmethod
  def by_player(cls, player, order=None):
    query = cls.all().filter('players =', player.nickname)
    if order: query.order(order)
    return query.fetch(1000)


class Goal(db.Model):
  time = db.IntegerProperty(required=True) # seconds since kickoff
  match = db.ReferenceProperty(required=True) # Key to Match
  player = db.StringProperty(required=True)
  team = db.StringProperty(required=True) # red, blue
  position = db.StringProperty(required=True) # back, front
  team_mate = db.StringProperty(required=True) # player's teammate
  opponent_back = db.StringProperty(required=True)
  opponent_front = db.StringProperty(required=True)

  @classmethod
  def by_match(cls, match, order=None):
    query = cls.all().filter('match =', match)
    if order: query.order(order)
    return query.fetch(1000)

  @classmethod
  def by_player(cls, player, order=None):
    query = cls.all().filter('player =', player.nickname)
    if order: query.order(order)
    return query.fetch(1000)


class PlayerStats(db.Model):
  player = db.ReferenceProperty(Player, required=True)
  date = db.DateTimeProperty(required=True)
  matches_played = db.IntegerProperty(required=True)
  goals_scored = db.IntegerProperty(required=True)
  goals_conceded = db.IntegerProperty(required=True)
  lethality = db.FloatProperty(required=False)
  pwnability = db.FloatProperty(required=False)
  awesomeness = db.FloatProperty(required=False)
  
  @classmethod
  def by_player(cls, player, order=None, limit=1000):
    query = cls.all().filter('player =', player)
    if order: query.order(order)
    if limit == 1:
      return query.get()
    else:
      return query.fetch(limit)

  @classmethod
  def update_for_player_and_match(cls, player, match):
    history = cls.by_player(player, order='-date')
    if not history:
      cls.rebuild_for_player(player)
      return

    cls.new_stats(player, match, history[0])

  @classmethod
  def rebuild_for_player(cls, player):
    stats = cls.by_player(player)
    matches = Match.by_player(player, order='kickoff')

    if stats: db.delete(stats)

    previous_stats = None
    for match in matches:
      previous_stats = cls.new_stats(player, match, previous_stats)

  @classmethod
  def all_players_latest(cls):
    players = Player.all().fetch(1000)
    stats = {}
    for player in players:
      player_stats = cls.by_player(player, order='-date', limit=1)
      stats[player.nickname] = player_stats
    return stats

  @classmethod
  def new_stats(cls, player, match, previous=None):
    if previous:
      goals_scored = previous.goals_scored
      goals_conceded = previous.goals_conceded
      matches_played = previous.matches_played
    else:
      goals_scored = 0
      goals_conceded = 0
      matches_played = 0

    goals = Goal.by_match(match)
    scored = [1 for goal in goals if goal.player == player.nickname]
    conceded = [1 for goal in goals if goal.opponent_back == player.nickname]
    matches_played += 1
    goals_scored += len(scored)
    goals_conceded += len(conceded)

    try:
      awesomeness = float(goals_scored) / float(goals_conceded)
    except ZeroDivisionError:
      awesomeness = 0.0

    player_stats = cls(player=player,
                       date=match.kickoff,
                       matches_played=matches_played,
                       goals_scored=goals_scored,
                       goals_conceded=goals_conceded,
                       lethality=float(goals_scored) / float(matches_played),
                       pwnability=float(goals_conceded) / float(matches_played),
                       awesomeness=awesomeness)
    player_stats.put()
    return player_stats
