(function($) {

var App = function() {
  this.init();
};

App.prototype.init = function() {
  this.root = $('#app');

  this.styles = {};
  this.moods = {};

  this.root.find('.style_selector a').on('click', _.bind(this.styleClick, this));
  this.root.find('.mood_selector a').on('click', _.bind(this.moodClick, this));

  this.root.find('.next').on('click', _.bind(this.nextClick, this));

  this.root.find('.add_button').on('click', _.bind(this.addClick, this));

  $('#search').on('click', _.bind(this.search, this));

  this.$player = $('#player');

  this.$message = $('.message');
  this.$tracks = $('.tracks');

  this.$playlists = $('.playlists select');

  this.setupPlayer();
};

App.prototype.setupPlayer = function() {
  var listener = "rdio_callback";

  var params = {
    'allowScriptAccess': 'always'
  };

  var attributes = {};

  var domain = document.location.host.split(':')[0]

  var flashvars = {
    'playbackToken': playback_token, // global
    'domain': domain,
    'listener': listener
  };

  swfobject.embedSWF('http://www.rdio.com/api/swf/', // the location of the Rdio Playback API SWF
    'apiswf', // the ID of the element that will be replaced with the SWF
    1, 1, '9.0.0', 'expressInstall.swf', flashvars, params, attributes);
};

App.prototype.styleClick = function(e) {
  var el = $(e.target);
  var sel = el.closest('.style_selector');
  sel.find('.selected').removeClass('selected');
  el.addClass('selected');
  this.styles[sel.data('selector')] = el.data('style');
  this.debounceSearch();
  return false;
};

App.prototype.moodClick = function(e) {
  var el = $(e.target);
  var sel = el.closest('.mood_selector');
  sel.find('.selected').removeClass('selected');
  el.addClass('selected');
  this.moods[sel.data('selector')] = el.data('mood');
  this.debounceSearch();
  return false;
};

App.prototype.nextClick = function() {
  this.getPlayer().rdio_next();
  return false;
};

App.prototype.addClick = function() {
  var self = this;

  if (!this.playingTrack) {
    this.message('No track playing');
    return;
  }

  var playlist = this.$playlists.val();

  $.ajax({
    url: '/add',
    data: {
      playlist: playlist,
      track: this.playingTrack['key']
    },
    success: function() {
      self.message('Added ' + self.playingTrack['name'] + ' to playlist.');
    }
  });
};

App.prototype.debounceSearch = function() {
  var self = this;
  if (this.searchTimeout) {
    window.clearTimeout(this.searchTimeout);
  }
  this.searchTimeout = window.setTimeout(function() {
    self.search();
  }, 3000);
};

App.prototype.search = function() {
  // construct url from params
  var data = {};

  _.each(this.styles, function(style, key) {
    data[key] = style;
  });

  _.each(this.moods, function(mood, key) {
    data[key] = mood;
  });

  $.ajax({
    url: '/search',
    data: data,
    success: _.bind(this.processResults, this)
  });
};

App.prototype.message = function(msg) {
  var self = this;
  if (this._messageShowing) {
    setTimeout(function() {
      self.message(msg);
    }, 1000);
  }
  this.$message.text(msg);
  this.$message.fadeIn();
  this._messageShowing = true;
  setTimeout(function() {
    self.$message.fadeOut(function() {
      self.$message.text('');
    });
    self._messageShowing = false;
  }, 5000);
};

App.prototype.processResults = function(result) {
  var self = this;

  var keys = _.keys(result.songs);
  var count = keys.length;

  if (!count) {
    this.message('No results found!');
    return;
  } else {
    this.$player.show();
  }

  // clear current queue
  this.getPlayer().rdio_clearQueue();
  this.toQueue = [];

  this.message('Found ' + count + ' songs');

  // save songs, trigger play
  this.songs = _.shuffle(keys);

  // play first song
  this.getPlayer().rdio_play(this.songs[0]);

  // get the rest ready to queue
  this.toQueue = this.songs.slice(1);
};

App.prototype.queueIfNeeded = function() {
  if (!this.toQueue.length) {
    return;
  }

  this.getPlayer().rdio_queue(this.toQueue.shift());
};

App.prototype.updateQueueMessage = function(queue) {
  var msg = '';
  var parts = [];
  if (this.styles['style1']) {
    parts.push(this.styles['style1']);
  }
  if (this.styles['style2']) {
    parts.push(this.styles['style2']);
  }
  if (this.moods['mood1']) {
    parts.push(this.moods['mood1']);
  }
  if (this.moods['mood2']) {
    parts.push(this.moods['mood2']);
  }
  msg = 'now playing ' + queue.length + ' ' + parts.join(' ') + ' tracks.';
  this.$tracks.text(msg);
};

App.prototype.getPlayer = function() {
  return $('#apiswf')[0];
};

App.prototype.updatePlayer = function(song) {
  this.playingTrack = song;

  if (!song) {
    return;
  }

  // update player display
  this.$player.find('.art img.main').attr('src', song.icon.replace('200', '600'));
  this.$player.find('.art img.reflection').attr('src', song.icon.replace('200', '600'));
  this.$player.find('.artist').text(song.artist).attr('href', song.artistUrl);
  this.$player.find('.album').text(song.album).attr('href', song.albumUrl);
  this.$player.find('.song').text(song.name).attr('href', song.url);
};

$(document).ready(function() {
  window.app = new App();

  function log() {
    if (console && console.log) {
      console.log.apply(console, arguments);
    }
  }

  window.rdio_callback = {
    ready: function() {
      log('player ready');
      rdio.ready();
    },
    
    playStateChanged: function(playState) {
      // The playback state has changed.
      // The state can be: 0 - paused, 1 - playing, 2 - stopped, 3 - buffering or 4 - paused.
      log('playstate changed ' + playState);
      //$('#playState').text(playState);
    },

    playingTrackChanged: function(playingTrack, sourcePosition) {
      // The currently playing track has changed.
      // Track metadata is provided as playingTrack and the position within the playing source as sourcePosition.
      log('playingTrackChanged',arguments);
      if (playingTrack != null) {
        //$('#track').text(playingTrack['name']);
        //$('#album').text(playingTrack['album']);
        //$('#artist').text(playingTrack['artist']);
        //$('#art').attr('src', playingTrack['icon']);
      }
      app.updatePlayer(playingTrack);
      app.queueIfNeeded();
    },

    playingSourceChanged: function(playingSource) {
      // The currently playing source changed.
      // The source metadata, including a track listing is inside playingSource.
      log('playingSourceChanged',arguments);
    },

    volumeChanged: function(volume) {
      // The volume changed to volume, a number between 0 and 1.
      log('volumeChanged',arguments);
    },

    muteChanged: function(mute) {
      // Mute was changed. mute will either be true (for muting enabled) or false (for muting disabled).
      log('muteChanged',arguments);
    },

    positionChanged: function(position) {
      //The position within the track changed to position seconds.
      // This happens both in response to a seek and during playback.
      //$('#position').text(position);
      log('positionChanged',arguments);
    },

    queueChanged: function(newQueue) {
      // The queue has changed to newQueue.
      log('queueChanged',arguments);
      app.queueIfNeeded();
      app.updateQueueMessage(newQueue);
    },

    shuffleChanged: function(shuffle) {
      // The shuffle mode has changed.
      // shuffle is a boolean, true for shuffle, false for normal playback order.
      log('shuffleChanged',arguments);
    },

    repeatChanged: function(repeatMode) {
      // The repeat mode change.
      // repeatMode will be one of: 0: no-repeat, 1: track-repeat or 2: whole-source-repeat.
      log('repeatChanged',arguments);
    },

    playingSomewhereElse: function() {
      // An Rdio user can only play from one location at a time.
      // If playback begins somewhere else then playback will stop and this callback will be called.
      log('playingSomewhereElse',arguments);
    }
  };
});

})(jQuery);
