import Core as Core


if __name__ == "__main__":
    creds = 'credentials.txt'

    playlist = 'Techno'

    output_path = r'C:\Users\26656\Music'
    client = Core.YoutubeDL(creds, output_path)
    client.get_current_playlists()
    client.select_playlist('Techno')
    client.download_playlist()






