var foos = {};

foos.goals = [];

foos.players = {
  'red_front': null,
  'red_back': null,
  'blue_front': null,
  'blue_back': null,
};

foos.scores = {
  'red': 0,
  'blue': 0
};

foos.kickOff = 0;


foos.init = function() {
  setTimeout(function() { window.scrollTo(0, 1); }, 0);

  function connect(id, eventName, handler) {
    var element = document.getElementById(id);
    element.addEventListener(eventName, handler, false);
  }
  for (var key in foos.players) {
    connect(key, 'click', foos.goal);
  }
  connect('swap_red', 'click', foos.swapPlayers);
  connect('swap_blue', 'mousedown', foos.swapPlayers);
  connect('undo', 'click', foos.undo);
  connect('done', 'click', foos.submit);
  connect('start', 'click', foos.startMatch);
  foos.populateSelects();
};


foos.populateSelects = function(id) {
  var allPlayers = PLAYERS;
  var cookie = util.getCookie('players');
  var currentPlayers = cookie ? cookie.split(',').reverse() : allPlayers;
  var index = 0;
  for (var key in foos.players) {
    var select = document.getElementById('select_' + key);
    for (var i = 0, player; player = allPlayers[i]; ++i) {
      var option = document.createElement('option');
      if (player == currentPlayers[index]) {
        option.selected = true;
      }
      option.value = player;
      option.textContent = player;
      select.appendChild(option);
    }
    index++;
  }
};


foos.startMatch = function() {
  foos.kickOff = (new Date()).getTime();

  var players = [];
  for (var key in foos.players) {
    var select = document.getElementById('select_' + key);
    foos.players[key] = select.value;
    var button = document.getElementById(key);
    util.toggleElement(button);
    util.toggleElement(select);
    button.textContent = foos.players[key].substr(0, 3);
    players.push(select.value);
  }

  util.setCookie('players', players.join(','), 7);

  util.toggleElement('swap_red');
  util.toggleElement('swap_blue');
  util.toggleElement('undo');
  util.toggleElement('done');
  util.toggleElement('start');
};


foos.goal = function(e) {
  var target = e.currentTarget;
  var id = target.id;
  var player = target.textContent;
  var team = id.split('_')[0];
  var position = id.split('_')[1];
  var otherPosition = position == 'front' ? 'back' : 'front';
  var opponent = team == 'red' ? 'blue' : 'red';

  var goal = {
    'time': (new Date()).getTime() - foos.kickOff,
    'player': foos.players[id],
    'team': team,
    'position': position,
    'team_mate': foos.players[team + '_' + otherPosition],
    'opponent_back': foos.players[opponent + '_back'],
    'opponent_front': foos.players[opponent + '_front'],
  }

  foos.goals.push(goal);
  foos.increaseScore(team);
};


foos.increaseScore = function(team, opt_delta) {
  var scoreSpan = document.getElementById('score_' + team);
  scoreSpan.textContent = foos.scores[team] += opt_delta ? opt_delta : 1;
};


foos.swapPlayers = function(e) {
  var team = e.currentTarget.id.split('_')[1];

  var temp = foos.players[team + '_front'];
  foos.players[team + '_front'] = foos.players[team + '_back'];
  foos.players[team + '_back'] = temp;

  temp = document.getElementById(team + '_front').textContent;
  document.getElementById(team + '_front').textContent =
      document.getElementById(team + '_back').textContent;
  document.getElementById(team + '_back').textContent = temp;
};


foos.undo = function(e) {
  var goal = foos.goals.pop();
  if (goal) {
    foos.increaseScore(goal['team'], -1);
  }
};


foos.submit = function() {
  // Quick-n-dirt json serialiser.
  var lines = [];
  for (var i = 0, goal; goal = foos.goals[i]; ++i) {
    var tokens = [];
    for (var key in goal) {
      var datum = goal[key];
      if (typeof(datum) === 'string') datum = '"' + datum + '"';
      tokens.push('"' + key + '":' + datum);
    }
    lines.push('{' + tokens.join(',') + '}');
  }

  var players = [];
  for (var key in foos.players) {
    players.push(foos.players[key]);
  }

  var json = '{' +
    '"kickoff":' + foos.kickOff + ',' +
    '"players":["' + players.join('","') + '"],' +
    '"goals":[' + lines.join(',') + ']' +
  '}';

  document.getElementById('json_data').value = json;
  document.getElementById('form').submit();
};


window.addEventListener('load', foos.init, false);
