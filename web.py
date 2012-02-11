import os

import sqlite3
from flask import Flask, render_template, url_for, redirect, request, session
from rdio import Rdio
from pprint import pprint

DATABASE = 'genredio.db'

# get env vars
SECRET_KEY = os.environ.get('DB_SECRET')
USERNAME = os.environ.get('DB_USERNAME')
PASSWORD = os.environ.get('DB_PASSWORD')
APP_SECRET = os.environ.get('APP_SECRET')

# setup app
app = Flask(__name__)
app.secret_key = APP_SECRET

# setup rdio api vars
rdio_key = os.environ.get('RDIO_API_KEY')
rdio_secret = os.environ.get('RDIO_API_SECRET')
#, rdio_state)

def get_api():
  # access token and access token secret
  token = session.get('at')
  secret = session.get('ats')
  if token and secret:
    api = Rdio((rdio_key, rdio_secret), (token, secret))
  else:
    api = Rdio((rdio_key, rdio_secret))
  return api

@app.route('/')
def index():
  profile = None
  api = get_api()

  if api.token:
    user = api.call('currentUser')
    if user.has_key('result'):
      profile = user['result']

  return render_template('index.html', profile=profile)

@app.route('/login')
def login():
  api = get_api()

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
