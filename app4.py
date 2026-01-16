import requests
import urllib.parse
from datetime import datetime
from flask import Flask, redirect, request, session, jsonify
import pandas as pd

app = Flask(__name__)
app.secret_key = "super_secret_key"

CLIENT_ID = "232872f3ed3e4b6583f53dca73e4f3fc"
CLIENT_SECRET = "b2ce6e57722f43c6aa1510fea65b44a3"
REDIRECT_URI = "http://127.0.0.1:8000/callback"

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1"
SCOPE = "playlist-read-private playlist-read-collaborative"

@app.route("/")
def index():
    return '<h2>SpotiFit</h2><a href="/login">Login with Spotify</a>'

@app.route("/login")
def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=token_data)
    token_info = response.json()

    session["access_token"] = token_info["access_token"]
    session["expires_at"] = datetime.now().timestamp() + token_info["expires_in"]

    return redirect("/playlists")

@app.route("/playlists")
def playlists():
    if "access_token" not in session:
        return redirect("/login")

    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    response = requests.get(
        f"{API_BASE_URL}/me/playlists",
        headers=headers
    )

    if response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch playlists",
            "status_code": response.status_code,
            "response": response.text
        }), 400

    data = response.json()

    result = []
    for playlist in data.get("items", []):
        result.append({
            "name": playlist["name"],
            "id": playlist["id"]
        })

    return jsonify(result)


@app.route("/analyze/<playlist_id>")
def analyze(playlist_id):
    if "access_token" not in session:
        return jsonify({"error": "Not logged in"}), 401

    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    playlist_response = requests.get(
        f"{API_BASE_URL}/playlists/{playlist_id}",
        headers=headers,
        params={
            "market": "from_token",
            "fields": "tracks.items(track(id,name))"
        }
    )

    if playlist_response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch playlist",
            "status_code": playlist_response.status_code,
            "response": playlist_response.text
        }), 400

    playlist_data = playlist_response.json()
    tracks_items = playlist_data["tracks"]["items"]

    track_ids = []
    for item in tracks_items:
        if item.get("track") and item["track"].get("id"):
            track_ids.append(item["track"]["id"])

    if not track_ids:
        return jsonify({"error": "No tracks found"}), 400

    features_response = requests.get(
        f"{API_BASE_URL}/audio-features",
        headers=headers,
        params={"ids": ",".join(track_ids[:100])}
    )

    if features_response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch audio features",
            "status_code": features_response.status_code,
            "response": features_response.text
        }), 400

    features = features_response.json().get("audio_features")
    clean_features = [f for f in features if f is not None]

    df = pd.DataFrame(clean_features)

    if df.empty:
        return jsonify({"error": "No valid audio features"}), 400

    profile = df[["danceability", "energy", "tempo", "valence"]].mean()

    return jsonify(profile.to_dict())

@app.route("/recommend/<playlist_id>")
def recommend(playlist_id):
    if "access_token" not in session:
        return jsonify({"error": "Not logged in"}), 401

    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    tracks_response = requests.get(
        f"{API_BASE_URL}/playlists/{playlist_id}/tracks",
        headers=headers,
        params={
            "market": "from_token",
            "limit": 100
        }
    )

    if tracks_response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch tracks",
            "status_code": tracks_response.status_code,
            "response": tracks_response.text
        }), 400

    tracks = tracks_response.json()

    seed_tracks = []
    for item in tracks["items"]:
        if item.get("track") and item["track"].get("id"):
            seed_tracks.append(item["track"]["id"])
        if len(seed_tracks) == 5:
            break

    if not seed_tracks:
        return jsonify({"error": "No seed tracks found"}), 400

    recs_response = requests.get(
        f"{API_BASE_URL}/recommendations",
        headers=headers,
        params={
            "seed_tracks": ",".join(seed_tracks),
            "limit": 10
        }
    )

    if recs_response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch recommendations",
            "status_code": recs_response.status_code,
            "response": recs_response.text
        }), 400

    recs = recs_response.json()

    result = []
    for t in recs["tracks"]:
        result.append({
            "song": t["name"],
            "artist": t["artists"][0]["name"],
            "preview": t["preview_url"]
        })

    return jsonify(result)

if __name__ == "__main__":
    app.run(port=8000, debug=True)
