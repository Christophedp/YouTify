import Core as Core


if __name__ == "__main__":
    creds = 'credentials.txt'

    playlist = 'Techno'

    output_path = r'C:\Users\26656\Music'
    client = Core.YoutubeDL(creds, output_path)
    client.get_current_playlists()
    client.select_playlist('Techno')
    client.get_playlist_tracks()

    for i in range(len(client.tracks)):
        track = client.tracks[i]
        print('Track No:', i)
        youtube_track_data = client.youtube_search_track(track)

        # input("Press Enter to continue...")
        client.youtube_download_audio(youtube_track_data, track)








