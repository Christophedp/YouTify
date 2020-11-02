"""
Youtube music downloader. Uses Spotify to retrieve song details.
"""
import json
import requests
import base64
import datetime
import os
import sys
import time
import webbrowser
import eyed3
import pandas as pd
import numpy as np
from urllib.parse import urlencode

pd.options.mode.chained_assignment = None  # default='warn'


class YoutubeDL(object):
    def __init__(self, credentials, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.client_id = None
        self.client_secret = None
        self.token = None
        self.expires = None
        self.expired = True
        self.now = None
        self.data = None
        self.playlist_name = None
        self.classified = None
        self.classification_file = None
        self.client_credentials_64 = None
        self.auth_code = None
        self.refresh_token = None

        # Playlists
        self.playlist = None
        self.playlists = None
        self.playlist_name = None
        self.playlist_href = None
        self.playlist_id = None
        self.tracks = None

        # Audacity
        self.to_pipe = None
        self.from_pipe = None
        self._eol = None

        self.creds_path = credentials

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
        self.authorization_code(self.creds_path)

        # Load user data
        user_data = self.get_user_profile()

        self.display_name = user_data['display_name']
        self.user_id = user_data['id']
        print(f'Welcome {self.display_name}!')

        self.auth_header = {
            'Authorization': f'Bearer {self.token}'
        }

        # Start pipe to Audacity
        self.init_audacity_pipe()

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
        with open('refresh_token.txt') as f_token:
            try:
                self.refresh_token = f_token.readlines()[0]
                # Get new access token
                self.renew_token()

            except IndexError:
                # Get authorization code
                with open('auth_code.txt') as f_auth:
                    try:
                        self.auth_code = f_auth.readlines()[0]
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
            webbrowser.open(response.url, new=1)
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
        print(response.status_code)
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
            with open('refresh_token.txt', 'w') as f:
                f.write(self.refresh_token)
            print('Refresh token saved for future use. Authorization is now granted!')

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

        query_params = {
            'limit': 50,
            'offset': 0
        }

        response = requests.get(self.playlists_url, params=query_params, headers=header)
        valid_response = response.status_code in range(200, 299)

        if valid_response:
            playlist_data = response.json()
            self.playlists = playlist_data['items']

    def select_playlist(self, playlist_name = None):
        self.playlist_name = playlist_name

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
                if item['name'] == playlist_name:
                    _idx = i
            if _idx == 1000:
                print('Specified playlist not found, exiting...')
                exit()

        self.playlist = self.playlists[_idx]
        self.playlist_name = self.playlist['name']
        self.playlist_href = self.playlist['href']
        self.playlist_id = self.playlist['id']

        print(self.playlist.keys())
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
                'fields': 'items(track(name,artists(name,href),album(name,release_date),duration_ms,id,href,uri))',
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
        #     print(track)

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




    """
    AUDACITY METHODS
    """

    def init_audacity_pipe(self):
        # Platform specific constants
        if sys.platform == 'win32':
            print("recording-test.py, running on windows")
            pipe_to_audacity = '\\\\.\\pipe\\ToSrvPipe'
            pipe_from_audacity = '\\\\.\\pipe\\fromsrvpipe'
            self._eol = '\r\n\0'
        else:
            print("recording-test.py, running on linux or mac")
            pipe_to_audacity = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
            pipe_from_audacity = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
            self._eol = '\n'

        try:
            self.to_pipe = open(pipe_to_audacity, 'w')
            print("-- File to write to has been opened")
        except FileNotFoundError:
            print('Pipe to audacity does not exist. Ensure Audacity is running with mod-script-pipe.')
            exit()

        try:
            self.from_pipe = open(pipe_from_audacity, 'r')
            print("-- File to read from has now been opened too\r\n")
        except FileNotFoundError:
            print('Pipe from audacity does not exist. Ensure Audacity is running with mod-script-pipe.')
            exit()

    def send_command(self, command):
        """Send a command to Audacity."""
        print("Send: >>> " + command)
        self.to_pipe.write(command + self._eol)
        self.to_pipe.flush()

    def get_response(self):
        """Get response from Audacity."""
        line = self.from_pipe.readline()
        result = ""
        while True:
            result += line
            line = self.from_pipe.readline()
            # print(f"Line read: [{line}]")
            if line == '\n':
                return result

    def do_command(self, command):
        """Do the command. Return the response."""
        self.send_command(command)
        # time.sleep(0.1) # may be required on slow machines
        response = self.get_response()
        print("Rcvd: <<< " + response)
        return response

    def test_pipe(self):
        self.do_command('TrackClose')
        self.do_command("Record2ndChoice")
        time.sleep(20)
        self.do_command('Stop')
        self.do_command("Select: Track=0 mode=Set")
        # Select entire track
        self.do_command("SelTrackStartToEnd")
        # Remove silence
        self.do_command('TruncateSilence')
        self.do_command(r'Export2: Filename=D:\chris\Music\test.mp3')


if __name__ == "__main__":
    playlist_dir = r'D:\chris\Documents\Google\Takeout\YouTube en YouTube Music\playlists'
    playlist_name = r'\vink-ik-leuks.json'

    playlist_path = playlist_dir + playlist_name
    creds = 'credentials.txt'

    client = YoutubeDL(creds)
    client.get_current_playlists()
    client.select_playlist('Techno')
    client.get_playlist_tracks()
    client.get_playing_track()
    # client.play_single_track(0)
    client.record_single_track(-7)

    # test = client.get_user_profile()
    # print(test.json())


    # client.read_json(playlist_path)
    test = 'Sub Focus & Wilkinson - Just Hold On (Sub Focus & Wilkinson vs. Pola & Bryson Remix)'
    # data_df = client.read_json(playlist_path)
    # client.check_classification(data_df)


    # print(data_df['Title'])
    # client.search_track(test)
    # df_classified = client.classify_manual(data_df)
    # client.check_classification(df_classified)







