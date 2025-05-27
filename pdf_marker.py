#!/usr/bin/python3
# PDF Regex Marker – rounded-corner edition

import gi, re, threading, click, pdftotext, os, shutil, sys, subprocess, tempfile
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk          # ← Gdk added for key-handler

import toc_creator
from pdfoutline_mod import pdfoutline


# ────────── global rounded-corner CSS ──────────
CSS = b"""
.rounded-window {
    border-radius: 16px;
    border: 1px solid @borders;
}
.rounded-window > headerbar,
.rounded-window > .titlebar              { border-radius: 16px 16px 0 0; }
.rounded-window > headerbar > .background,
.rounded-window > .titlebar > .background{ border-radius: 16px 16px 0 0; }
.rounded-window > * {
    border-radius: 16px;
    background-color: @theme_bg_color;
}
"""
provider = Gtk.CssProvider()
provider.load_from_data(CSS)
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(),
    provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
)


# ────────── paths / globals ──────────
home_folder              = os.path.expanduser('~')
input_folder             = f'{home_folder}/pdf-regex-marker/directories/input_folder'
regexes_folder           = f'{home_folder}/pdf-regex-marker/directories/regexes'
text_record_folder       = f'{home_folder}/pdf-regex-marker/directories/text_record'
completed_records_folder = f'{home_folder}/pdf-regex-marker/directories/completed_records'

toc_file                 = f'{home_folder}/pdf-regex-marker/directories/TOC/toc.txt'
combined_pdf_path        = f'{input_folder}/combined.pdf'
completed_record_pdf     = f'{completed_records_folder}/completed_record.pdf'
redo_completed_record_pdf= f'{completed_records_folder}/redo_completed_record.pdf'


# ──────────────────────────── UI ────────────────────────────
class PDFMarker(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="PDF Regex Marker")
        self.add_css_class("rounded-window")        # ← apply rounded style

        # Dark mode (optional but matches your other apps)
        Gtk.Settings.get_default().set_property(
            "gtk-application-prefer-dark-theme", True
        )

        # Grid -------------------------------------------------
        grid = Gtk.Grid(
            column_spacing=1, row_spacing=15,
            margin_top=35, margin_bottom=35,
            margin_start=21, margin_end=20,
        )
        self.set_child(grid)

        # Ctrl+Q shortcut -------------------------------------
        ctrl_q = Gtk.ShortcutController()
        ctrl_q.add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<Control>q"),
                Gtk.CallbackAction.new(self.quit_app),
            )
        )
        self.add_controller(ctrl_q)

        # ——— DIRECTORY BUTTONS ———
        self._label(grid, "<b>DIRECTORIES</b>", 0)

        self._make_btn(grid, "Input",       self.input_folder,       0, 1)
        self._make_btn(grid, "REGEX",       self.regex_folder,       1, 1)
        self._make_btn(grid, "TextRecord",  self.text_file_folder,   2, 1)
        self._make_btn(grid, "Completed",   self.completed_records,  3, 1)

        # ——— PROCESSING BUTTONS ———
        self._label(grid, "<b>PROCESSING</b>", 2)

        self._make_btn(grid, "TOC",       self.toc_file,   0, 3)
        self._make_btn(grid, "CreateTOC", self.CreateTOC,  1, 3)
        self._make_btn(grid, "BookMark",  self.BookMark,   2, 3)
        self._make_btn(grid, "RunBoth",   self.RunBoth,    3, 3)

        # ——— Progress bars ———
        self.progress_bar = Gtk.ProgressBar(show_text=True, margin_top=15)
        grid.attach(self.progress_bar, 0, 4, 4, 1)

        self.page_progress_bar = Gtk.ProgressBar(show_text=True)
        grid.attach(self.page_progress_bar, 0, 5, 4, 1)

    # ───────── helpers ─────────
    def _make_btn(self, grid, label, cb, col, row):
        btn = Gtk.Button(label=label)
        btn.set_size_request(150, -1)
        btn.connect("clicked", cb)
        grid.attach(btn, col, row, 1, 1)

    def _label(self, grid, markup, row):
        lbl = Gtk.Label()
        lbl.set_markup(markup)
        lbl.set_halign(Gtk.Align.START)
        grid.attach(lbl, 0, row, 7, 1)

    # ───────── directory handlers ─────────
    def input_folder(self, *_):       click.launch(input_folder)
    def regex_folder(self, *_):       click.launch(regexes_folder)
    def text_file_folder(self, *_):   click.launch(text_record_folder)
    def toc_file(self, *_):           click.launch(toc_file)
    def completed_records(self, *_):  click.launch(completed_records_folder)

    # ───────── progress updaters ─────────
    def update_progress(self, frac):
        GLib.idle_add(self.progress_bar.set_fraction, frac)
        GLib.idle_add(self.progress_bar.set_text,
                      f"Creating TOC File: {int(frac*100)}%")

    def update_page_progress(self, frac):
        GLib.idle_add(self.page_progress_bar.set_fraction, frac)
        GLib.idle_add(self.page_progress_bar.set_text,
                      f"Applying Bookmarks: {int(frac*100)}%")

    # ───────── actions (each runs in its own thread) ─────────
    def CreateTOC(self, *_):
        threading.Thread(target=self._run_create_toc, daemon=True).start()
    def _run_create_toc(self):
        toc_creator.create_toc(
            text_record_folder, input_folder, combined_pdf_path,
            toc_file, regexes_folder, self.update_progress
        )
        GLib.idle_add(click.launch, toc_file)

    def BookMark(self, *_):
        threading.Thread(target=self._run_pdfoutline, daemon=True).start()
    def _run_pdfoutline(self):
        pdfoutline(
            combined_pdf_path, toc_file, completed_record_pdf,
            gs='gs', update_progress=self.update_page_progress
        )
        GLib.idle_add(click.launch, completed_record_pdf)

    def RunBoth(self, *_):
        threading.Thread(target=self._run_both, daemon=True).start()
    def _run_both(self):
        toc_creator.create_toc(
            text_record_folder, input_folder, combined_pdf_path,
            toc_file, regexes_folder, self.update_progress
        )
        pdfoutline(
            combined_pdf_path, toc_file, completed_record_pdf,
            gs='gs', update_progress=self.update_page_progress
        )
        GLib.idle_add(click.launch, completed_record_pdf)

    # ───────── quit / key handler ─────────
    def on_key_pressed(self, _ctrl, keyval, keycode, state):
        if Gdk.keyval_name(keyval) in ("Return", "KP_Enter"):
            self.calculate(None)   # if you later add a calculate() method

    def quit_app(self, *_):
        self.get_application().quit()


# ──────────────────────────── Application ───────────────────────────
class PDFMarkerApp(Gtk.Application):
    def do_activate(self, *_):
        PDFMarker(self).present()

    def do_startup(self):
        Gtk.Application.do_startup(self)


if __name__ == "__main__":
    PDFMarkerApp().run(None)

