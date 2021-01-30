To install:
- Ensure latest version of youtube-dl is installed (https://pypi.org/project/youtube_dl/)
	If using pycharm, install by activating venv in command window and using pip.
- Ensure FFmpeg is installed. To do this, download, extract and copy the three executables in the bin directory to a directory included in the python path. E.g. the pycharm project directory.
	(https://www.ffmpeg.org/)

- On first use, you will have to give permission for the code to access your Spotify Playlist data.
To do this, run main.py and log into your Spotify account. Next, copy the code from the URL on the resulting webpage.
This URL should have the format "http://localhost:8888/callback?code=YOURCODE". Copy YOURCODE to the empty auth_code.txt file.
Run the code a second time, and it should now work!

Robin laat effe weten of dit werkt. :D
