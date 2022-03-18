import Core as Core


if __name__ == "__main__":
    output_path = r'D:\chris\Music\YouTify'
    client = Core.YoutubeDL(output_path)
    client.download_playlist('Deep House')







