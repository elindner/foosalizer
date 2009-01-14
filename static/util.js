util = {};

util.MILLIS_IN_A_DAY = 86400000;
util.COOKIE_PREPEND = 'foosalizer_';


util.toggleElement = function(elementOrId) {
  var element;
  if (typeof(elementOrId) == 'string') {
    element = document.getElementById(elementOrId);
  } else {
    element = elementOrId;
  }
  var classes = element.className.split(' ');
  var index = classes.indexOf('hidden');
  if (index !== -1) {
    classes.splice(index, 1);
  } else {
    classes.push('hidden');
  }
  element.className = classes.join(' ');
};


util.setCookie = function(name, value, days) {
  var expires = '';
  if (days) {
    var date = new Date();
    date.setTime(date.getTime() + (days * util.MILLIS_IN_A_DAY));
    var expires = '; expires=' + date.toGMTString();
  }
  name = util.COOKIE_PREPEND + name;
  document.cookie = name + '=' + value + expires + '; path=/';
}


util.getCookie = function(name) {
  name = util.COOKIE_PREPEND + name + '=';
  var parts = document.cookie.split(';');
  for(var i = 0, part; part = parts[i]; ++i) {
    while (part.charAt(0) == ' ') {
      part = part.substring(1, part.length);
    }
    if (part.indexOf(name) == 0) {
      return part.substring(name.length, part.length);
    }
  }
  return null;
}


util.deleteCookie = function(name) {
  util.setCookie(name, '', -1);
}

