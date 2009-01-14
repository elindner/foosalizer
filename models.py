#!/usr/bin/env python

from google.appengine.ext import db


class Player(db.Model):
  # Should I use UserProperty? Why?
  nickname = db.StringProperty(required=True)


class Match(db.Model):
  creator = db.StringProperty(required=True)
  kickoff = db.DateTimeProperty(required=True)
  players = db.StringListProperty()


class Goal(db.Model):
  time = db.IntegerProperty(required=True) # seconds since kickoff
  match = db.ReferenceProperty(required=True) # Key to Match
  player = db.StringProperty(required=True)
  team = db.StringProperty(required=True) # red, blue
  position = db.StringProperty(required=True) # back, front
  team_mate = db.StringProperty(required=True) # player's teammate
  opponent_back = db.StringProperty(required=True)
  opponent_front = db.StringProperty(required=True)
