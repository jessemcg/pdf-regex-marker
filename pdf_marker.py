#!/usr/bin/python3

import gi
import re
import threading
import click
import pdftotext
import os
import shutil
import sys
import subprocess
import tempfile, os, sys
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import toc_creator
from pdfoutline_mod import pdfoutline

# Global Variables
# Directories
home_folder = os.path.expanduser('~')
input_folder = os.path.join(home_folder, 'pdf-regex-marker/directories/input_folder')
regexes_folder = os.path.join(home_folder, 'pdf-regex-marker/directories/regexes')
text_record_folder = os.path.join(home_folder, 'pdf-regex-marker/directories/text_record')
completed_records_folder = os.path.join(home_folder, 'pdf-regex-marker/directories/completed_records')

# Files
toc_file = os.path.join(home_folder, 'pdf-regex-marker/directories/TOC/toc.txt')
combined_pdf_path = os.path.join(home_folder, 'pdf-regex-marker/directories/input_folder/combined.pdf')
completed_record_pdf = os.path.join(home_folder, 'pdf-regex-marker/directories/completed_records/completed_record.pdf')
redo_completed_record_pdf = os.path.join(home_folder, 'pdf-regex-marker/directories/completed_records/redo_completed_record.pdf')

class PDFMarker(Gtk.ApplicationWindow):
        
    def __init__(self, app):
        super().__init__(application=app, title="PDF Regex Marker")

        # Grid
        grid = Gtk.Grid()
        grid.set_column_spacing(1)
        grid.set_row_spacing(15)
        grid.set_margin_top(35)
        grid.set_margin_bottom(35)
        grid.set_margin_start(21)
        grid.set_margin_end(20)
        
        # Set the grid as the child of the window
        self.set_child(grid)
        
        # Create a ShortcutController
        shortcut_controller = Gtk.ShortcutController.new()
        self.add_controller(shortcut_controller)

        # Create a shortcut for Control+Q
        key_combination = Gtk.ShortcutTrigger.parse_string("<Control>q")
        shortcut = Gtk.Shortcut.new(key_combination, Gtk.CallbackAction.new(self.quit_app))
        shortcut_controller.add_shortcut(shortcut)
        
        # Label for directores
        self.outline_prog_label = Gtk.Label()
        self.outline_prog_label.set_markup("<b>DIRECTORIES</b>") # label
        grid.attach(self.outline_prog_label, 0, 0, 7, 1)
        self.outline_prog_label.set_halign(Gtk.Align.START)  # Align to the left

        # Button Definitions
        # Input
        self.input_folder_button = Gtk.Button(label="Input")
        self.input_folder_button.set_size_request(150, -1)  # width and height
        self.input_folder_button.connect("clicked", self.input_folder)
        grid.attach(self.input_folder_button, 0, 1, 1, 1)
        
        # REGEX
        self.regex_folder_button = Gtk.Button(label="REGEX")
        self.regex_folder_button.set_size_request(150, -1)  # width and height
        self.regex_folder_button.connect("clicked", self.regex_folder)
        grid.attach(self.regex_folder_button, 1, 1, 1, 1)
        
        # Text Record      
        self.text_file_folder_button = Gtk.Button(label="TextRecord")
        self.text_file_folder_button.set_size_request(150, -1)  # width and height
        self.text_file_folder_button.connect("clicked", self.text_file_folder)
        grid.attach(self.text_file_folder_button, 2, 1, 1, 1)
        
        # Completed
        self.completed_records_button = Gtk.Button(label="Completed")
        self.completed_records_button.set_size_request(150, -1)  # width and height
        self.completed_records_button.connect("clicked", self.completed_records)
        grid.attach(self.completed_records_button, 3, 1, 1, 1)
        
        # Label for Processsing
        self.outline_prog_label = Gtk.Label()
        self.outline_prog_label.set_markup("<b>PROCESSING</b>") # label
        grid.attach(self.outline_prog_label, 0, 2, 7, 1)
        self.outline_prog_label.set_halign(Gtk.Align.START)  # Align to the left
        
        # TOC
        self.toc_file_button = Gtk.Button(label="TOC")
        self.toc_file_button.set_size_request(150, -1)  # width and height
        self.toc_file_button.connect("clicked", self.toc_file)
        grid.attach(self.toc_file_button, 0, 3, 1, 1)
        
        # Run
        self.run_button = Gtk.Button(label="Run")
        self.run_button.set_size_request(150, -1)  # width and height
        self.run_button.connect("clicked", self.run)
        grid.attach(self.run_button, 1, 3, 1, 1)
        
        # Redo Run
        self.redo_button = Gtk.Button(label="ReDo")
        self.redo_button.set_size_request(150, -1)  # width and height
        self.redo_button.connect("clicked", self.redo)
        grid.attach(self.redo_button, 2, 3, 1, 1)
        
        # Create an event controller for key presses
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)
        
        # Progress Bars
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)  # Show progress text
        grid.attach(self.progress_bar, 0, 4, 4, 1)  # Adjust grid position as needed
        self.progress_bar.set_margin_top(15)
        
        self.page_progress_bar = Gtk.ProgressBar()
        self.page_progress_bar.set_show_text(True)
        grid.attach(self.page_progress_bar, 0, 5, 4, 1)  # Adjust position as needed

    # Button Functionality
    def input_folder(self, widget):
        click.launch(input_folder)

    def regex_folder(self, widget):
        click.launch(regexes_folder)

    def text_file_folder(self, widget):
        click.launch(text_record_folder)

    def toc_file(self, widget):
        click.launch(toc_file)
        
    def completed_records(self, widget):
        click.launch(completed_records_folder)
        
    def update_progress(self, progress):
        GLib.idle_add(self.progress_bar.set_fraction, progress)
        GLib.idle_add(self.progress_bar.set_text, f"Creating TOC File: {int(progress * 100)}%")
        
    def update_page_progress(self, progress):
        GLib.idle_add(self.page_progress_bar.set_fraction, progress)
        GLib.idle_add(self.page_progress_bar.set_text, f"Applying Bookmarks: {int(progress * 100)}%")

	# Running Tasks (need separate threads to make progress bar work)
    def run(self, widget):
        # Create a new thread for the create_toc function
        thread = threading.Thread(target=self.run_create_toc, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()

    def run_create_toc(self):
        toc_creator.create_toc(text_record_folder, input_folder, combined_pdf_path, toc_file, regexes_folder, self.update_progress)
        pdfoutline(combined_pdf_path, toc_file, completed_record_pdf, gs='gs', update_progress=self.update_page_progress)
        GLib.idle_add(click.launch, completed_record_pdf)

    def redo(self, widget):
        # Create a new thread for the redo operation
        thread = threading.Thread(target=self.redo_pdfoutline, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()

    def redo_pdfoutline(self):
        pdfoutline(combined_pdf_path, toc_file, redo_completed_record_pdf, gs='gs', update_progress=self.update_page_progress)
        GLib.idle_add(click.launch, redo_completed_record_pdf)
        
    # Quit with control+Q  
    def on_key_pressed(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == "Return" or keyname == "KP_Enter":
            self.calculate(None)

    def quit_app(self, *args):
        self.get_application().quit()
        
class PDFMarkerApp(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_activate(self):
        win = PDFMarker(self)
        win.present()  # Use present instead of show

    def do_startup(self):
        Gtk.Application.do_startup(self)

def main():
    win = ProgressBarWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

app = PDFMarkerApp()
app.run(None)

        
        
        
