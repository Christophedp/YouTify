To install:
- Ensure FFmpeg is installed. To do this, download the latest version of FFmpeg from https://www.ffmpeg.org/download.html. Extract and copy the three executables in the bin directory to a directory included in the python path, e.g. the directory containing your Pycharm project.

- On first use, you will have to give permission for the code to access your Spotify Playlist data.
To do this, create an instance of Core.YoutubeDL(), which will prompt a login screen. Log into your Spotify account. Next, copy the code from the URL on the resulting webpage.
This URL should have the format "http://localhost:8888/callback?code=YOURCODE". Copy YOURCODE to the empty auth_code.txt file.
Run the code a second time, and it should now work!

Robin laat effe weten of dit werkt. :D