import os
import uuid

from flask import Flask, jsonify, session, request, redirect
from flask_session import Session
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app_secrets import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)


caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get('uuid')


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
        scope='user-library-read user-read-currently-playing',
        cache_handler=cache_handler
    )

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return f'<marquee><h1>Welcome to Branden\'s Spotify Hackathon Project</h1></marquee>' \
               f'<h2> Click Sign In to link your Spotify account' \
               f'<br/><a href="{auth_url}">Sign in</a></h2>'

    # Step 4. Signed in, display data
    sp = spotipy.Spotify(auth_manager=auth_manager)
    results = sp.current_user_saved_tracks()
    artists = set()
    for item in results["items"]:
        for artist in item["track"]["artists"]:
            artists.add(artist["name"])
    return jsonify(list(artists))


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
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    track = spotify.current_user_playing_track()
    if not track is None:
        return track
    return "No track currently playing."

#
# @app.route("/saved_tracks")
# def spotify_auth():
#     sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
#                                                    client_secret=CLIENT_SECRET,
#                                                    redirect_uri=REDIRECT_URI,
#                                                    scope="user-library-read"))
#
#     results = sp.current_user_saved_tracks()
#     artists = set()
#     for item in results["items"]:
#         for artist in item["track"]["artists"]:
#             artists.add(artist["name"])
#     return jsonify(list(artists))
#     # return jsonify(results["items"])
