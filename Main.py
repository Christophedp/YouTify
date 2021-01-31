import Core as Core


if __name__ == "__main__":
    # playlist_dir = r'D:\chris\Documents\Google\Takeout\YouTube en YouTube Music\playlists'
    # playlist_name = r'\vink-ik-leuks.json'

    # playlist_path = playlist_dir + playlist_name
    creds = 'credentials.txt'

    playlist = 'Techno'

    output_path = r'C:\Users\26656\Music'
    client = Core.YoutubeDL(creds, output_path)
    client.get_current_playlists()
    client.select_playlist('Techno')
    client.get_playlist_tracks()
    # client.get_playing_track()

    for i in range(len(client.tracks)):
        print('Track No:', i)
        youtube_track_data = client.youtube_search_track(client.tracks[i])

        # input("Press Enter to continue...")
        client.youtube_download_audio(youtube_track_data)


    # client.play_single_track(0)
    # client.record_single_track(-7)

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







