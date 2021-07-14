import os
import uuid

from flask import Flask, jsonify, session, request, redirect, render_template
from flask_session import Session
import spotipy

from app_secrets import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from exceptions import SessionInvalid

app = Flask(__name__,
            static_url_path='',
            static_folder='static',
            template_folder='static/templates')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

SCOPE = "user-library-read user-read-currently-playing user-top-read"
caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get('uuid')


def verify_session(scope):
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        cache_handler=cache_handler
    )

    if auth_manager.validate_token(cache_handler.get_cached_token()):
        return cache_handler, auth_manager
    else:
        raise SessionInvalid()


@app.route('/')
def index():
    if not session.get('uuid'):
        # Step 1. Visitor is unknown, give random ID
        session['uuid'] = str(uuid.uuid4())

    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=cache_handler
    )

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return render_template("index.html", auth_url=auth_url)

    # Step 4. Signed in, display data
    sp_api_client = spotipy.Spotify(auth_manager=auth_manager)
    results = sp_api_client.current_user_saved_tracks(limit=50)

    songs = list()

    for song in results["items"]:
        song_dict = dict()
        song_dict["name"] = song["track"]["name"]
        song_dict["album_art"] = song["track"]["album"]["images"][1]["url"]
        song_dict["artists"] = [artist["name"] for artist in song["track"]["artists"]]
        song_dict["added_time"] = song["added_at"]
        song_dict["preview_url"] = song["track"]["preview_url"]
        songs.append(song_dict)

    return render_template("index.html", songs=songs, uuid=session['uuid'])


@app.route('/sign_out')
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect('/')


@app.route('/currently_playing')
def currently_playing():
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=cache_handler
    )

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    track = spotify.current_user_playing_track()
    if not track is None:
        return track
    return "No track currently playing."


@app.route('/top_artists')
def top_artists():
    try:
        cache_handler, auth_manager = verify_session(SCOPE)
    except SessionInvalid:
        return redirect('/')

    sp_api_client = spotipy.Spotify(auth_manager=auth_manager)
    return jsonify(sp_api_client.current_user_top_artists(limit=9))
