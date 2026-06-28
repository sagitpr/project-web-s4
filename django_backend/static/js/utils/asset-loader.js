/**
 * Warungio Asset Path Helper — Django /static/ URLs
 */
(function () {
  'use strict';

  var STATIC_PREFIX = '/static/';

  var Assets = {
    img: function (name) { return STATIC_PREFIX + 'images/' + name; },
    js: function (name) { return STATIC_PREFIX + 'js/' + name; },
    css: function (name) { return STATIC_PREFIX + 'css/' + name; },
    favicon: function (name) { return STATIC_PREFIX + (name || 'favicon.ico'); },
    video: function (name) { return STATIC_PREFIX + 'video/' + name; },
    url: function (path) {
      if (path.indexOf('/static/') === 0) return path;
      if (path.indexOf('images/') === 0) return STATIC_PREFIX + path;
      return path;
    },
  };

  window.WarungioAssets = Assets;
})();
