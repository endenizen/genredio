import os, urllib2

from flask import Flask, render_template, url_for, redirect, request, session, jsonify
from werkzeug.contrib.cache import SimpleCache
from rdio import Rdio
from pyechonest import song, artist

# echonest id bucket
BUCKET = 'rdio-US'

# setup app
app = Flask(__name__)
app.secret_key = os.environ.get('APP_SECRET')

# setup cache
cache = SimpleCache()

# setup rdio api vars
rdio_key = os.environ.get('RDIO_API_KEY')
rdio_secret = os.environ.get('RDIO_API_SECRET')
playback_token = None

# echonest data (will do requests on startup)
# Note: echonest api key should be setup as env variable
# and not in this file. Name should be ECHO_NEST_API_KEY
styles = artist.list_terms('style')
moods = artist.list_terms('mood')

def get_rdio_api():
  """ create user-specific or generic rdio api """
  token = session.get('at')
  secret = session.get('ats')
  if token and secret:
    api = Rdio((rdio_key, rdio_secret), (token, secret))
  else:
    api = Rdio((rdio_key, rdio_secret))
  return api

def get_playback_token():
  """ returns a playback token for the flash player """
  token = cache.get('playback_token')
  if token:
    return token

  api = get_rdio_api()
  result = api.call('getPlaybackToken', { 'domain': request.host.split(':')[0] })
  playback_token = result['result']
  cache.set('playback_token', playback_token, 600)
  return playback_token

def echonest_search(styles, moods):
  """ performs the search on echonest with the given styles and moods """
  cache_key = 'echo_%s_%s' % (styles, moods)
  result = cache.get(cache_key)
  if result:
    return result
  try:
    songs = song.search(
        style=styles,
        mood=moods,
        buckets=['id:%s' % BUCKET, 'tracks'],
        limit=True,
        results=100)
    # Stopped working with rdio-US bucket change
    # TODO: switch back when it starts working again
    #foreign_ids = [s.get_foreign_id(BUCKET) for s in songs]
    foreign_ids = [s.cache['tracks'][0]['foreign_id'] for s in songs]
    keys = [str(f.split(':')[-1]) for f in foreign_ids]
  except:
    # return empty list if there was an error
    return []
  cache.set(cache_key, keys, 600)
  return keys

@app.route('/')
def index():
  profile = None
  playlist_list = None
  api = get_rdio_api()

  if api.token:
    user = api.call('currentUser')
    if user.has_key('result'):
      profile = user['result']
    playlists = api.call('getPlaylists')
    if playlists.has_key('result'):
      playlist_list = playlists['result']

  playback_token = get_playback_token()

  return render_template('index.html', profile=profile, styles=styles, moods=moods, playback_token=playback_token, playlists=playlist_list)

@app.route('/search')
def search():
  params = dict([part.split('=') for part in request.query_string.split('&')])

  def clean_style(style):
    # clean url-encoded styles: 'big+band' 'r%26b'
    return urllib2.unquote(style).replace('+', ' ')

  # grab selected styles
  styles = []
  for style in ('style1', 'style2'):
    if params.has_key(style):
      styles.append(clean_style(params[style]))

  moods = []
  for mood in ('mood1', 'mood2'):
    if params.has_key(mood):
      moods.append(clean_style(params[mood]))

  # get rdio keys for songs from echonest
  keys = echonest_search(styles, moods)

  # get rdio songs from keys
  api = get_rdio_api()
  result = api.call('get', {
    'keys': ','.join(keys),
    'extras': '-*,key,name,artist,album,icon,shortUrl'
  })
  rdio_songs = result['result']

  return jsonify(songs=rdio_songs)

@app.route('/add')
def add():
  params = dict([part.split('=') for part in request.query_string.split('&')])

  playlist = params['playlist']
  track = params['track']

  api = get_rdio_api()
  result = api.call('addToPlaylist', {
    'playlist': playlist,
    'tracks': track
  })

  return jsonify(result=result)

@app.route('/login')
def login():
  api = get_rdio_api()

  callback_url = request.host_url + url_for('login_callback')[1:]
  url = api.begin_authentication(callback_url)

  session['rt'] = api.token[0]
  session['rts'] = api.token[1]

  return redirect(url)

@app.route('/login_callback')
def login_callback():
  params = dict([part.split('=') for part in request.query_string.split('&')])
  token = session['rt']
  secret = session['rts']
  api = Rdio((rdio_key, rdio_secret), (token, secret))
  api.complete_authentication(params.get('oauth_verifier'))
  session['rt'] = None
  session['rts'] = None
  session['at'] = api.token[0]
  session['ats'] = api.token[1]
  return redirect(url_for('index'))

@app.route('/logout')
def logout():
  session['rt'] = None
  session['rts'] = None
  session['at'] = None
  session['ats'] = None
  return redirect(url_for('index'))

if __name__ == '__main__':
  # Bind to PORT if defined, otherwise default to 5000.
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
