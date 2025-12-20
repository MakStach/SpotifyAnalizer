import urllib.parse
import requests
import json
from datetime import datetime, timedelta    

from flask import Flask
from flask import jsonify
from flask import request 
from flask import redirect
from flask import session

app= Flask(__name__)
app.secret_key = 'supersecretkey'
access_token = 'access_token'
client_id = '232872f3ed3e4b6583f53dca73e4f3fc'
client_secret = 'b2ce6e57722f43c6aa1510fea65b44a3'
redirect_uri = 'http://127.0.0.1:8000/callback'

Auth_url = 'https://accounts.spotify.com/authorize'
Token_url = 'https://accounts.spotify.com/api/token'
API_base_url = 'https://api.spotify.com/v1/'    
scope = 'user-read-private user-read-email playlist-read-private playlist-read-collaborative'

@app.route('/')
def index():
    return 'Spotify OAuth2 <a href="/login">Login with Spotify</a>'

@app.route('/login')
def login():
    scope = 'user-read-private user-read-email playlist-read-private playlist-read-collaborative'
    auth_query_parameters = {
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scope,
        'client_id': client_id
       # 'show_dialog': True
    }

    auth_url = f"{Auth_url}?{urllib.parse.urlencode(auth_query_parameters)}"

    return redirect(auth_url)

@app.route('/callback')
def callback():
    print("Callback called")
    if 'error' in request.args:
        return f"Error: {request.args['error']}"
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }
        response = requests.post(Token_url, data=req_body)
        token_info = response.json()
        print("Token Info: ")
        print (token_info)

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']  
        
        return redirect('/playlists')
    

@app.route('/playlists')
def get_playlists():
    if access_token not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')
    headers = {
        'authorization': f"Bearer {session['access_token']}"
    }
    response = requests.get(f"{API_base_url}me/playlists", headers=headers)
    playlists = response.json()
    return jsonify(playlists)

@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() < session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': client_id,
            'client_secret': client_secret
        }
        response = requests.post(Token_url, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']
        
        return redirect('/playlists')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port= (8000), debug=True),