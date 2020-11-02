import os
import sys
import time
import json




def send_command(command):
    """Send a command to Audacity."""
    print("Send: >>> "+command)
    TOPIPE.write(command + EOL)
    TOPIPE.flush()


def get_response():
    """Get response from Audacity."""
    line = FROMPIPE.readline()
    result = ""
    while True:
        result += line
        line = FROMPIPE.readline()
        # print(f"Line read: [{line}]")
        if line == '\n':
            return result


def do_command(command):
    """Do the command. Return the response."""
    send_command(command)
    # time.sleep(0.1) # may be required on slow machines
    response = get_response()
    print("Rcvd: <<< " + response)
    return response


def play_record(filename):
    """Import track and record to new track.
    Note that a stop command is not required as playback will stop at end of selection.
    """
    do_command(f"Import2: Filename={os.path.join(PATH, filename + '.wav')}")
    do_command("Select: Track=0")
    do_command("SelTrackStartToEnd")
    # Our imported file has one clip. Find the length of it.
    clipsinfo = do_command("GetInfo: Type=Clips")
    clipsinfo = clipsinfo[:clipsinfo.rfind('BatchCommand finished: OK')]
    clips = json.loads(clipsinfo)
    duration = clips[0]['end'] - clips[0]['start']
    # Now we can start recording.
    do_command("Record2ndChoice")
    print('Sleeping until recording is complete...')
    time.sleep(duration + 0.1)


def export(filename):
    """Export the new track, and deleted both tracks."""
    do_command("Select: Track=1 mode=Set")
    do_command("SelTrackStartToEnd")
    do_command(f"Export2: Filename={os.path.join(PATH, filename)} NumChannels=1.0")
    do_command("SelectAll")
    do_command("RemoveTracks")


def do_one_file(name):
    """Run test with one input file only."""
    play_record(name)
    export(name + "-out.wav")


def quick_test():
    """Quick test to ensure pipe is working."""
    do_command('Help: CommandName=Help')


if __name__ == '__main__':
    # Platform specific constants
    if sys.platform == 'win32':
        print("recording-test.py, running on windows")
        PIPE_TO_AUDACITY = '\\\\.\\pipe\\ToSrvPipe'
        PIPE_FROM_AUDACITY = '\\\\.\\pipe\\FromSrvPipe'
        EOL = '\r\n\0'
    else:
        print("recording-test.py, running on linux or mac")
        PIPE_TO_AUDACITY = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
        PIPE_FROM_AUDACITY = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
        EOL = '\n'

    try:
        TOPIPE = open(PIPE_TO_AUDACITY, 'w')
        print("-- File to write to has been opened")
    except FileNotFoundError:
        print('Pipe to audacity does not exist. Ensure Audacity is running with mod-script-pipe.')
        exit()

    try:
        FROMPIPE = open(PIPE_FROM_AUDACITY, 'r')
        print("-- File to read from has now been opened too\r\n")
    except FileNotFoundError:
        print('Pipe from audacity does not exist. Ensure Audacity is running with mod-script-pipe.')
        exit()

    quick_test()

    do_command('TrackClose')

    do_command("Record2ndChoice")
    time.sleep(20)
    do_command('Stop')
    do_command("Select: Track=0 mode=Set")
    # Select entire track
    do_command("SelTrackStartToEnd")
    # Remove silence
    do_command('TruncateSilence')   
    do_command(r'Export2: Filename=D:\chris\Music\test.mp3')
               
   


