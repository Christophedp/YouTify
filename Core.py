"""
Youtube music downloader. Uses Spotify to retrieve song details.
TO DO:
- Check if mp3 file exists at the start of the searching process. This should save a lot of time.
"""
import json
import requests
import base64
import datetime
import os
import re
import stat
import time
import webbrowser
import eyed3
import youtube_dlc
import yt_dlp
import pandas as pd
import numpy as np
import tkinter as tk
from urllib.parse import urlencode
from youtube_search import YoutubeSearch
from fast_youtube_search import search_youtube
from GUI import GUIStart

pd.options.mode.chained_assignment = None  # default='warn'


class YoutubeDL(object):
    def __init__(self, output_path=None, credentials=None, *args, **kwargs):
        self.client_id = None
        self.client_secret = None
        self.token = None
        self.expires = None
        self.expired = True
        self.now = None
        self.data = None
        self.classified = None
        self.classification_file = None
        self.client_credentials_64 = None
        self.auth_code = None
        self.refresh_token = None

        # Set audio format
        self.audio_format = 'mp3'

        # Playlists
        self.playlist = None
        self.playlists = []
        self.playlist_name = None
        self.playlist_href = None
        self.playlist_id = None
        self.tracks = None
        self.chosen_playlist = None

        # Output
        if output_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.output_path = os.path.join(script_dir, 'Output')
        else:
            self.output_path = output_path

        print('Outputting to:', self.output_path)

        self.creds_path = 'credentials.txt'

        # URLs for Spotify API
        authenticate_url = r'https://accounts.spotify.com/'
        base_url = r'https://api.spotify.com/v1/'
        self.token_url = authenticate_url + r'api/token'
        self.search_url = base_url + r'search'
        self.me_url = base_url + r'me'
        self.authorization_url = authenticate_url + r'authorize'
        self.playlists_url = self.me_url + r'/playlists'
        self.play_url = self.me_url + r'/player/play'
        self.pasue_url = self.me_url + r'/player/pause'

        self.redirect_uri = r'http://localhost:8888/callback'

        # Authenticate
        self.auth_code_file = 'auth_code.txt'            # Text file to store authorization code
        self.refresh_token_file = 'refresh_token.txt'    # Text file to store refresh token

        if not os.path.exists(self.auth_code_file):
            open(self.auth_code_file, 'a').close()
        if not os.path.exists(self.refresh_token_file):
            open(self.refresh_token_file, 'a').close()

        self.authorization_code(self.creds_path)

        # Load user data
        user_data = self.get_user_profile()

        self.display_name = user_data['display_name']
        self.user_id = user_data['id']
        print(f'Welcome {self.display_name}!')

        self.auth_header = {
            'Authorization': f'Bearer {self.token}'
        }

    def authorization_code(self, credentials):
        # Load client ID and client secret
        if self.client_id is None or self.client_secret is None:
            try:
                with open(credentials) as f:
                    lines = f.readlines()
                    self.client_id = lines[0].strip('\n')
                    self.client_secret = lines[1].strip('\n')
            except FileNotFoundError:
                raise Exception('Please provide a valid path to the credentials file.')
            # Credentials must be Base64 encoded
            client_credentials = f'{self.client_id}:{self.client_secret}'
            self.client_credentials_64 = base64.b64encode(client_credentials.encode())

        # Check if a refresh token exists. If yes, use this to get a new token.
        with open(self.refresh_token_file) as f_token:
            try:
                self.refresh_token = f_token.readlines()[0]
                # Get new access token
                self.renew_token()

            except IndexError:
                print('NO REFRESH TOKEN')
                # Get authorization code
                with open(self.auth_code_file) as f_auth:
                    try:
                        self.auth_code = f_auth.readlines()[0]
                        # Remove state if included in the authorization  code
                        if '#' in self.auth_code:
                            self.auth_code = self.auth_code.split('#')[0]

                    except IndexError:
                        self.get_authorization_code()
                # Get refresh token
                self.get_refresh_token()

    def get_authorization_code(self):
        # Scopes required
        scopes = ['user-read-playback-state',
                  'user-library-modify',
                  'user-read-currently-playing',
                  'user-modify-playback-state',
                  'streaming',
                  'playlist-modify-private',
                  'playlist-modify-public',
                  'playlist-read-private',
                  'user-read-private'
        ]
        scopes = ' '.join(scopes)

        # Load authorization code - must be renewed if new user
        authorization_data = {
            'client_id': f'{self.client_id}',
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': scopes
        }

        response = requests.get(self.authorization_url, params=authorization_data)
        valid_request = response.status_code in range(200, 299)

        if valid_request:
            # print('Opening browser')
            webbrowser.open(response.url, new=1)
        # Run again with cookies now enabled?
        # res = requests.get(self.authorization_url)
        # print(res.url)
        # print(requests.get(res.url).text)
        print('Please paste authorization code in auth_code.txt.')
        exit()

    def get_refresh_token(self):
        # Exchange authorization code for access token
        token_body = {
            'grant_type': 'authorization_code',
            'code': f'{self.auth_code}',
            'redirect_uri': self.redirect_uri
        }

        token_headers = {
            'Authorization': f'Basic {self.client_credentials_64.decode()}'
        }

        response = requests.post(self.token_url, data=token_body, headers=token_headers)
        # print(response.status_code)
        valid_request = response.status_code in range(200, 299)

        if valid_request:
            token_response = response.json()
            self.refresh_token = token_response['refresh_token']
            self.token = token_response['access_token']

            expires_in = token_response['expires_in']
            self.now = datetime.datetime.now()
            self.expires = self.now + datetime.timedelta(seconds=expires_in)
            self.expired = self.expires < self.now

            # Write for future use
            with open(self.refresh_token_file, 'w') as f:
                f.write(self.refresh_token)
            print('Refresh token saved for future use. Authorization is now granted!')
        else:
            print('Request not valid...')

    """
    Use the refresh token to refresh the access token.
    """
    def renew_token(self):
        token_body = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }

        token_headers = {
            'Authorization': f'Basic {self.client_credentials_64.decode()}'
        }

        response = requests.post(self.token_url, data=token_body, headers=token_headers)
        valid_response = response.status_code in range(200, 299)

        if valid_response:
            data = response.json()

            expires_in = data['expires_in']
            self.token = data['access_token']

            self.now = datetime.datetime.now()
            self.expires = self.now + datetime.timedelta(seconds=expires_in)
            self.expired = self.expires < self.now

            print(f'Obtained new token! Expires at {self.expires}.')
        else:
            print('Authentication failed. Exiting...')
            exit()

    def authentication(self, credentials):
        """
        Request Spotify token
        """
        client_credentials_64 = None
        if self.client_id is None or self.client_secret is None:
            try:
                with open(credentials) as f:
                    lines = f.readlines()
                    self.client_id = lines[0].strip('\n')
                    self.client_secret = lines[1].strip('\n')
            except FileNotFoundError:
                raise Exception('Please provide a valid path to the credentials file.')
            # Credentials must be Base64 encoded
            client_credentials = f'{self.client_id}:{self.client_secret}'
            client_credentials_64 = base64.b64encode(client_credentials.encode())

        self.token_data = {
            'grant_type': 'client_credentials'
        }
        self.token_headers = {
            'Authorization': f'Basic {client_credentials_64.decode()}'
        }

        self.get_token()

    def get_token(self):
        try:
            response = requests.post(self.token_url, data=self.token_data, headers=self.token_headers)
        except ConnectionError:
            print('Failed to connect to the Spotify API. Aborting...')
            exit()
        valid_request = response.status_code in range(200, 299)

        if valid_request:
            data = response.json()

            expires_in = data['expires_in']
            self.token = data['access_token']

            self.now = datetime.datetime.now()
            self.expires = self.now + datetime.timedelta(seconds=expires_in)
            self.expired = self.expires < self.now
        else:
            print('Authentication failed. Exiting...')
            exit()

    def _check_expired(self):
        self.now = datetime.datetime.now()
        self.expired = self.expires < self.now

        if self.expired:
            self.renew_token()

    def search_track(self, query):
        # Check if token has expired
        self._check_expired()

        # Preprocess query
        # .........

        search_header = {
            'Authorization': f'Bearer {self.token}'
        }
        search_data = {
            'q': f'{query}',
            'type': 'track'
        }

        search_data_url = urlencode(search_data)
        query_url = f'{self.search_url}?{search_data_url}'

        response = requests.get(query_url, headers=search_header)
        valid_request = response.status_code in range(200, 299)
        if valid_request:
            data = response.json()
            tracks = data['tracks']
            track_found = len(tracks['items']) > 0

            if track_found:
                for track in tracks['items']:
                    album = track['album']
                    artists = track['artists']
                    title = track['name']
                    id = track['id']

                    artists_names = []
                    artists_genres = []
                    for artist in artists:
                        artists_names.append(artist['name'])

                        # Retrieve artist genre(s) to get an indication of the song genre
                        href = artist['href']
                        artist_details = self.request_href(href).json()
                        artist_genres = artist_details['genres']
                        # print(artist['name'], artist_genres)
                        try:
                            artists_genres.append(artist_genres[0])
                        except IndexError:
                            pass

                    genre = list(set(artists_genres))
                    if len(artists_genres) > 1:
                        # Find most occurring genre, assume this is the correct one.
                        most_occurring_genre = max(set(artists_genres), key=artists_genres.count)
                        genre = [most_occurring_genre]
                        print('Multiple possible genres...')
                    elif len(genre) == 0:
                        print('No genre found...')
                        genre = ['None']

                    print(f'{", ".join(artists_names)} - {title} [Genre: {genre[0]}]')

            else:
                print('No matching songs found.')
        return track_found

    def request_href(self, href):
        self._check_expired()
        search_header = {
            'Authorization': f'Bearer {self.token}'
        }
        return requests.get(href, headers=search_header)

    def read_json(self, list_json):
        self.playlist_name = os.path.basename(list_json).split('.')[0]
        # Read youtube playlist JSON
        try:
            with open(list_json, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise Exception('File not found. Please specify a correct path.')

        # Check keys
        playlist_keys = list(data[0].keys())
        print('Playlist keys: ', playlist_keys)

        snippet_keys = list(data[0][playlist_keys[4]].keys())
        print('Video keys: ', snippet_keys)

        # Initialise DF
        index = np.linspace(0, len(data)-1, len(data))
        columns = ['Title', 'VideoId', 'Thumbnail', 'DateTime', 'channel']
        data_df = pd.DataFrame(index=index, columns=columns)
        data_df = data_df.fillna(method='ffill')

        # Thumbnail quality
        quality = 'high'

        i = 0
        for video in data:
            snippet = video['snippet']
            title = snippet['title']
            channel = snippet['channelTitle']
            video_id = snippet['resourceId']['videoId']
            timestamp = snippet['publishedAt']
            try:
                thumbnail = snippet['thumbnails'][quality]
            except KeyError:
                thumbnail = 'none'

            data_df.loc[i] = [title, video_id, thumbnail, timestamp, channel]
            i = i + 1

        # Check if this playlist has been (partially) classified for ML before
        self.classification_file = f'classification_{self.playlist_name}.txt'
        data_df['Classification'] = np.nan
        if os.path.exists(self.classification_file):
            lines = np.loadtxt(self.classification_file)
            self.classified = len(lines)
            if self.classified > 0:
                data_df.loc[:self.classified - 1]['Classification'] = lines[:, 1]
        else:
            self.classified = 0

        return data_df

    def classify_manual(self, df):
        """
        Prompt user to manually classify videos as song or other.
        """
        for i, video in df[self.classified:].iterrows():
            print(video['Title'])
            try:
                classification = int(input('Please specify 0 for other and 1 for a song.'))
            except ValueError:
                raise Exception('Please provide a numerical input.')
            if classification in range(2):
                df.loc[i]['Classification'] = classification
                with open(self.classification_file, 'a') as f:
                    f.write(f'{int(i)}\t{classification}\n')

        return df

    def check_classification(self, df):
        """
        Go through classified videos and check if Spotify recognises songs.
        """
        df['Found'] = np.nan

        for i, video in df[df['Classification'].isin(range(2))].iterrows():
            title = video['Title']
            print('\n', title)
            song_found = self.search_track(title)
            df.loc[i]['Found'] = song_found

    def get_user_profile(self):
        self._check_expired()

        header = {
            'Authorization': f'Bearer {self.token}'
        }

        response = requests.get(self.me_url, headers=header)
        valid_response = response.status_code in range(200, 299)

        if valid_response:
            user_data = response.json()

        return user_data

    def get_current_playlists(self):
        self._check_expired()

        header = {
            'Authorization': f'Bearer {self.token}'
        }

        _end = False
        _offset = 0
        while not _end:
            query_params = {
                'limit': 50,
                'offset': _offset
            }

            response = requests.get(self.playlists_url, params=query_params, headers=header)
            valid_response = response.status_code in range(200, 299)

            if valid_response:
                playlist_data = response.json()
                self.playlists = self.playlists + playlist_data['items']
                _offset = len(self.playlists)
                # Stop looping through playlists if the latest batch is smaller than 50
                _end = _offset % 50 != 0

    def collect_playlists(self, playlist_name=None):
        self.playlist_name = playlist_name

        # Retrieve list of playlists
        self.get_current_playlists()

        n_playlists = len(self.playlists)
        playlists = []

        if self.playlist_name is None:
            for i in range(n_playlists):
                item = self.playlists[i]
                playlists.append(item['name'])

        return playlists

    def select_playlist(self, playlist_name=None):
        self.playlist_name = self.clean_string(playlist_name)
        print('CLEAN PLAYLIST?', self.playlist_name)
        self.output_path = os.path.join(self.output_path, self.playlist_name)

        N_playlists = len(self.playlists)

        _idx = 1000
        if self.playlist_name is None:
            for i in range(N_playlists):
                item = self.playlists[i]
                print(f'Playlist {i + 1}: {item["name"]}')

            while _idx not in range(N_playlists):
                try:
                    _idx = int(input('Which playlist would you like to download?')) - 1
                except ValueError:
                    pass
                print('Please enter a valid playlist number.')

        else:
            for i in range(N_playlists):
                item = self.playlists[i]
                # print(item['name'])
                if item['name'] == playlist_name:
                    _idx = i
            if _idx == 1000:
                print('Specified playlist not found, exiting...')
                exit()

        self.playlist = self.playlists[_idx]
        self.playlist_name = self.playlist['name']
        self.playlist_href = self.playlist['href']
        self.playlist_id = self.playlist['id']

        print(f'Selected playlist {self.playlist_name}.')

    def get_playlist_tracks(self):
        self._check_expired()
        playlist_url = f'https://api.spotify.com/v1/playlists/{self.playlist_id}/tracks'

        header = {
            'Authorization': f'Bearer {self.token}'
        }

        n_tracks_returned = 100
        n_tracks = 0
        self.tracks = []
        while n_tracks_returned == 100:
            query_params = {
                # 'fields': 'items(track(name,artists(name,href),album(name,release_date),duration_ms,id,href,uri,images))',
                'limit': 100,
                'offset': n_tracks
            }

            response = requests.get(playlist_url, params=query_params, headers=header)
            valid_response = response.status_code in range(200, 299)

            if valid_response:
                playlist_tracks = response.json()
                response_tracks = playlist_tracks['items']
                n_tracks_returned = len(response_tracks)
                n_tracks = n_tracks + n_tracks_returned

                self.tracks = self.tracks + response_tracks

        # for track in self.tracks:
            # print(track)

    def play_single_track(self, idx):
        self._check_expired()

        track_data = self.tracks[idx]['track']
        print(track_data)
        artists_data = track_data['artists']

        track_uri = [track_data['uri']]
        track_name = track_data['name']
        track_artists = [artist['name'] for artist in artists_data]

        filename = f'{track_name} - {" & ".join(track_artists)}'

        query_params = {
            'device_id': r'MMDEVAPI\AudioEndpoints'
        }

        body_params = {
            'uris': track_uri
        }

        response = requests.put(self.play_url, data=json.dumps(body_params), headers=self.auth_header)
        if response.status_code == 204:
            print(f'Playing track: {track_name} by {" & ".join(track_artists)}')
        else:
            print(f'Invalid response ({response.status_code}). Try to toggle Spotify on the current device by playing'
                  ' a song.')

        return filename

    def pause_track(self):
        self._check_expired()

        response = requests.put(self.pasue_url, headers=self.auth_header)
        valid_response = response in range(200, 299)

        if valid_response:
            print('Track paused.')

    def get_playing_track(self):
        self._check_expired()

        response = requests.get(r'https://api.spotify.com/v1/me/player/currently-playing', headers=self.auth_header)
        valid_response = response.status_code in range(200, 299)

        if valid_response:
            try:
                data = response.json()
                item = data['item']
                title = item['name']
                artists = [artist['name'] for artist in item['artists']]
                print(f'Currently playing: {title} by {" & ".join(artists)}.')
            except json.decoder.JSONDecodeError:
                print('No track currently playing.')

    def record_single_track(self, idx):
        self._check_expired()
        # Pause currently playing track
        self.pause_track()
        # Get track duration
        track_data = self.tracks[idx]['track']
        track_duration = track_data['duration_ms']/1000.

        # --- Set up Audacity for recording ---
        # Close previous track
        self.do_command("Select: Track=0 mode=Set")
        self.do_command('TrackClose')
        # Start recording
        self.do_command("Record2ndChoice")
        # Play track
        time.sleep(0.1)
        filename = self.play_single_track(idx)
        # Wait till track finished playing
        time.sleep(0.5*(track_duration+2))
        # Stop recording
        self.do_command('Stop')
        self.do_command("Select: Track=0 mode=Set")
        # Select entire track
        self.do_command("SelTrackStartToEnd")
        # Remove silence
        self.do_command('TruncateSilence')
        self.do_command(r'Export2: Filename=D:\chris\Music\fresh_recorded.mp3')

        self.write_metadata(idx, filename)

    def write_metadata(self, idx, filename):
        filepath = r'D:\chris\Music\fresh_recorded.mp3'

        try:
            audiofile = eyed3.load(filepath)
            time.sleep(0.5)
        except FileNotFoundError:
            print('Audiofile not found.')

        print(audiofile)

        track_data = self.tracks[idx]['track']
        album = track_data['album']['name']

        artists = [artist['name'] for artist in track_data['artists']]
        artists = " & ".join(artists)
        # artists = u'artists'
        title = track_data['name']
        # ADD GENRE
        print(track_data.keys())
        audiofile.initTag()

        audiofile.tag.artist = artists
        audiofile.tag.album = album
        audiofile.tag.title = title

        audiofile.tag.save()

        os.rename(filepath, filepath.replace('fresh_recorded', filename))

    def write_metadata_new(self, track, filepath):
        try:
            audiofile = eyed3.load(filepath)
        except FileNotFoundError:
            print('Audiofile not found.')

        track_data = track['track']
        track_name = track_data['name']
        track_name = self.clean_string(track_name)

        album_data = track_data['album']
        album_name = album_data['name']
        album_img_url = album_data['images'][0]['url']

        # print('ALBUM KEYS:', album_data.keys())
        artists = track_data['artists']
        artist_names = self.list_artist_names(self, artists)
        artists_joined = ' '.join(artist_names)

        genre = self.guess_genre(artists)

        # Download album artwork from Spotify
        playlist_path = os.path.split(filepath)[0]
        temp_thumbnail = os.path.join(playlist_path, f'{track_name}.jpg')

        img_data = requests.get(album_img_url).content
        print('Downloading thumbnail...')
        with open(temp_thumbnail, 'wb') as handler:
            handler.write(img_data)

        audiofile.initTag()

        audiofile.tag.artist = artists_joined
        audiofile.tag.album = album_name
        audiofile.tag.title = track_name
        audiofile.tag.genre = genre
        audiofile.tag.images.set(3, open(temp_thumbnail, 'rb').read(), 'image/jpeg')

        audiofile.tag.save()
        # Remove thumbnail file
        os.remove(temp_thumbnail)

    def guess_genre(self, artists):
        artists_names = []
        artists_genres = []
        for artist in artists:
            artists_names.append(artist['name'])

            # Retrieve artist genre(s) to get an indication of the song genre
            href = artist['href']
            artist_details = self.request_href(href).json()
            artist_genres = artist_details['genres']
            try:
                artists_genres.append(artist_genres[0])
            except IndexError:
                pass

        genre = list(set(artists_genres))
        if len(artists_genres) > 1:
            # Find most occurring genre, assume this is the correct one.
            most_occurring_genre = max(set(artists_genres), key=artists_genres.count)
            genre = [most_occurring_genre]
            # print('Multiple possible genres...')
        elif len(genre) == 0:
            # print('No genre found...')
            genre = ['None']

        return genre[0]

    @staticmethod
    def list_artist_names(self, artists_data):
        artists = []
        for artist in artists_data:
            artists.append(artist['name'])
        return artists

    @staticmethod
    def clean_string(string):
        string = re.sub(r'[^0-9a-zA-Z\[\]() ,-]+', '', string)
        string = re.sub(r'\.', '', string)
        return string

    """
    YOUTUBE METHODS
    """

    def youtube_search_track(self, track, max_results=10):
        download = False
        best_match = None

        track_data = track['track']
        track_name = track_data['name']
        artists = track_data['artists']
        artist_names = self.list_artist_names(self, artists)

        # Construct title for MP3
        mp3_title = f'{", ".join(artist_names)} - {track_name}'
        mp3_title = self.clean_string(mp3_title)
        print('Title:', mp3_title)

        # Check if the song has already been downloaded. If yes (and overwrite is true), skip.
        filepath = os.path.join(self.output_path, f'{mp3_title}.{self.audio_format}')
        if os.path.exists(filepath):
            print('Song has already been downloaded. Skipping...')
        else:
            download = True
            artists_query = ' '.join(artist_names)
            search_query = f'{track_name} {artists_query}'
            print(f'Searcing for: {search_query}')

            n_attempts = 0
            success = False
            while n_attempts < 5 and not success:
                print('Search attempt...')
                try:
                    # yt_results = YoutubeSearch(search_query, max_results=max_results).to_dict()
                    yt_results = search_youtube(search_query.split(' '))
                    print(yt_results)
                    success = True
                except KeyError as e:
                    print('Youtube Search KeyError... Trying again...')
                    n_attempts = n_attempts + 1

            print('Finished searching...')
            # RUN SOMETHING HERE TO IDENTIFY THE MOST CORRECT SEARCH RESULT
            # print('Amount of results found:', len(yt_results))
            try:
                best_match = yt_results[0]
            except IndexError:
                print('Nothing found on YouTube?')

            id = best_match['id']
            suffix = f'/watch?v={id}'
            best_match['url_suffix'] = suffix

        output = {
            'Best match': best_match,
            'MP3 Title': mp3_title,
            'Download': download
        }

        return output

    def youtube_download_audio(self, youtube_search_output, track):
        # Unpack youtube search output
        video_data = youtube_search_output['Best match']
        mp3_title = youtube_search_output['MP3 Title']

        # Check if output path exists. If not, create and ensure write permission.
        if not os.path.isdir(self.output_path):
            os.makedirs(self.output_path)
            os.chmod(self.output_path, stat.S_IWRITE)

        # Create youtube downloader object
        suffix = video_data['url_suffix']
        yt_url = f'http://www.youtube.com{suffix}'
        filepath = os.path.join(self.output_path, f'{mp3_title}.{self.audio_format}')

        # Download
        print(f'Downloading from (url): {yt_url})')
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [
                {'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format,
                'preferredquality': '192'
                 }
            ],
            # 'writethumbnail': True,
            # 'prefer_ffmpeg': True,
            # 'keepvideo': False,
            'outtmpl': os.path.join(self.output_path, f'{mp3_title}.%(ext)s')
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            n_attempts = 0
            success = False
            while n_attempts < 10 and not success:
                try:
                    ydl.download([yt_url])
                    success = True
                except yt_dlp.utils.DownloadError:
                    print(f'Unable to extract video data... This was attempt {n_attempts}')
                n_attempts = n_attempts + 1

            if not success:
                print('Download failed.')

        # Add metadata
        self.write_metadata_new(track, filepath)

    def _rip_playlist(self):
        if self.playlist_id is not None:
            # Get playlist tracks
            self.get_playlist_tracks()

            # Loop through the tracks, search on Youtube and download.
            for _idx in range(len(self.tracks)):
                track = self.tracks[_idx]
                print('Track No:', _idx)

                youtube_track_data = self.youtube_search_track(track)
                video_data = youtube_track_data['Best match']
                download = youtube_track_data['Download']

                if download:
                    if video_data is None:
                        print('Song not found. Skipping.')
                    else:
                        self.youtube_download_audio(youtube_track_data, track)

    def download_playlist(self, playlist=None, *args, **kwargs):
        # Get playlists
        playlists = self.collect_playlists()

        # If the user has specified a playlist, download this one. Otherwise, fire-up GUI.
        if playlist is not None:
            playlist = self.clean_string(playlist)
            self.select_playlist(playlist)
        else:
            # Start GUI
            root = tk.Tk()
            gui = GUIStart(root, playlists, *args, **kwargs)
            root.mainloop()
            # Let user select a playlist
            self.chosen_playlist = gui.selected_playlists
            # Enter this choice
            # LIMIT TO ONE PLAYLIST FOR NOW
            self.select_playlist(self.chosen_playlist[0])

        # Download
        self._rip_playlist()



