import os
import sys
import time


class Audacity(object):
    def __init__(self):
        # Audacity
        self.to_pipe = None
        self.from_pipe = None
        self._eol = None
        # Start pipe to Audacity
        # self.init_audacity_pipe()

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
        print("cvd: <<< " + response)
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
