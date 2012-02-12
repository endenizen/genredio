import os

#import sqlite3
from flask import Flask, render_template, url_for, redirect, request, session, jsonify
from werkzeug.contrib.cache import SimpleCache
from rdio import Rdio
from pyechonest import song, artist
#from pprint import pprint

#DATABASE = 'genredio.db'

# get env vars
SECRET_KEY = os.environ.get('DB_SECRET')
USERNAME = os.environ.get('DB_USERNAME')
PASSWORD = os.environ.get('DB_PASSWORD')
APP_SECRET = os.environ.get('APP_SECRET')

# setup app
app = Flask(__name__)
app.secret_key = APP_SECRET

cache = SimpleCache()

# setup rdio api vars
rdio_key = os.environ.get('RDIO_API_KEY')
rdio_secret = os.environ.get('RDIO_API_SECRET')
playback_token = None

# echonest data
styles = artist.list_terms('style')
moods = artist.list_terms('mood')

def get_rdio_api():
  """ access token and access token secret """
  token = session.get('at')
  secret = session.get('ats')
  if token and secret:
    api = Rdio((rdio_key, rdio_secret), (token, secret))
  else:
    api = Rdio((rdio_key, rdio_secret))
  return api

def get_playback_token():
  token = cache.get('playback_token')
  if token:
    return token

  api = get_rdio_api()
  result = api.call('getPlaybackToken', { 'domain': request.host.split(':')[0] })
  playback_token = result['result']
  cache.set('playback_token', playback_token, 600)
  return playback_token

@app.route('/')
def index():
  profile = None
  api = get_rdio_api()

  if api.token:
    user = api.call('currentUser')
    if user.has_key('result'):
      profile = user['result']

  playback_token = get_playback_token()

  return render_template('index.html', profile=profile, styles=styles, moods=moods, playback_token=playback_token)

def echonest_search(styles, moods):
  cache_key = 'echo_%s_%s' % (styles, moods)
  app.logger.error('loading key %s' % cache_key)
  result = cache.get(cache_key)
  if result:
    return result
  app.logger.error('Hey the method is being called')
  try:
    songs = song.search(
        style=styles,
        mood=moods,
        buckets=['id:rdio-us-streaming'],
        limit=True,
        results=100)
    foreign_ids = [s.get_foreign_id('rdio-us-streaming') for s in songs]
    keys = [str(f.split(':')[-1]) for f in foreign_ids]
  except:
    return []
  cache.set(cache_key, keys, 600)
  return keys

@app.route('/search')
def search():
  params = dict([part.split('=') for part in request.query_string.split('&')])

  # grab selected styles
  styles = []
  for style in ('style1', 'style2'):
    if params.has_key(style):
      # sub + for space instead of url decoding
      styles.append(params[style].replace('+', ' '))

  moods = []
  for mood in ('mood1', 'mood2'):
    if params.has_key(mood):
      moods.append(params[mood].replace('+', ' '))

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
