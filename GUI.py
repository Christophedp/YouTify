import tkinter as tk
import re as re
from tkinter import ttk as ttk
import os as os


class GUIStart:
    def __init__(self, master, playlists, *args, **kwargs):
        # Initialise variables

        # Initialise GUI
        self.master = master
        master.title('Spotify Playlist Downloader')

        self.label_info = tk.Label(master, text='Welcome to the Spotify Playlist Downloader\n'
                                                'Please select a playlist.')

        # BUTTON
        row_button = 1
        self.button = tk.Button(master, text='Select', command=self.button_press)
        self.button.grid(row=row_button, columnspan=2)

        # VARIABLE CHECK BOXES

        self.checkboxes = []
        self.checkbox_vars = [0]*len(playlists)
        self.playlist_list = []

        i = 0
        for playlist in playlists:
            row = row_button + i + 1
            # Create a label and checkbox for each variable
            self.playlist_label = tk.Label(master, text=playlist)
            self.playlist_label.grid(row=row, column=1)

            # Create a variable for each checkbox, otherwise value will be lost
            self.checkbox_vars[i] = tk.Variable()
            checkbutton = ttk.Checkbutton(master, takefocus=0, variable=self.checkbox_vars[i])
            checkbutton.grid(row=row, column=0)

            self.checkboxes.append(checkbutton)
            self.playlist_list.append(playlist)
            i = i + 1

    def button_press(self):
        # Ensure a playlist is selected
        self.selected_playlists = []
        playlist_selected = False

        i = 0
        for button in self.checkboxes:
            playlist = self.playlist_list[i]
            if button.state():
                self.selected_playlists.append(playlist)
            i = i + 1

        if len(self.selected_playlists) != 0:
            playlist_selected = True
            self.master.destroy()
        else:
            print('Please select a playlist.')