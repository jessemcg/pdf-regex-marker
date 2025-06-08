#!/usr/bin/python3
# PDF Regex Marker – responsive GUI with GTK4

import gi, re, threading, click, pdftotext, os, shutil, sys, subprocess, tempfile
from pypdf import PdfReader, PdfWriter

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk  # Gdk needed for CSS provider

import toc_creator
from pdfoutline_mod import pdfoutline


# ────────── global rounded‑corner CSS ──────────
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
    Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
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
        self.add_css_class("rounded-window")
        self.set_default_size(600, 480)  # small default, but resizable

        # Force dark mode
        Gtk.Settings.get_default().set_property(
            "gtk-application-prefer-dark-theme", True
        )

        # ─── main layout: vertical box ───
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=20,
            margin_top=25,
            margin_bottom=25,
            margin_start=20,
            margin_end=20,
        )
        self.set_child(main_box)

        # Ctrl+Q shortcut (unchanged) --------------------------
        ctrl_q = Gtk.ShortcutController()
        ctrl_q.add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<Control>q"),
                Gtk.CallbackAction.new(self.quit_app),
            )
        )
        self.add_controller(ctrl_q)

        # ——— DIRECTORY SECTION ———
        dir_label = Gtk.Label(label="<b>DIRECTORIES</b>", use_markup=True)
        dir_label.set_halign(Gtk.Align.START)
        main_box.append(dir_label)

        dir_flow = self._make_flowbox()
        main_box.append(dir_flow)
        self._add_button(dir_flow, "Input", self.input_folder)
        self._add_button(dir_flow, "REGEX", self.regex_folder)
        self._add_button(dir_flow, "TextRecord", self.text_file_folder)
        self._add_button(dir_flow, "Completed", self.completed_records)

        # ——— PROCESSING SECTION ———
        proc_label = Gtk.Label(label="<b>PROCESSING</b>", use_markup=True)
        proc_label.set_halign(Gtk.Align.START)
        main_box.append(proc_label)

        proc_flow = self._make_flowbox()
        main_box.append(proc_flow)
        self._add_button(proc_flow, "TOC", self.toc_file)
        self._add_button(proc_flow, "CreateTOC", self.CreateTOC)
        self._add_button(proc_flow, "BookMark", self.BookMark)
        self._add_button(proc_flow, "RunBoth", self.RunBoth)

        # ——— Progress bars ———
        self.progress_bar = Gtk.ProgressBar(show_text=True, hexpand=True)
        main_box.append(self.progress_bar)

        self.page_progress_bar = Gtk.ProgressBar(show_text=True, hexpand=True)
        main_box.append(self.page_progress_bar)

    # ───────── helpers ─────────
    def _make_flowbox(self):
        fb = Gtk.FlowBox()
        fb.set_max_children_per_line(4)  # wraps automatically when window narrows
        fb.set_selection_mode(Gtk.SelectionMode.NONE)
        fb.set_column_spacing(8)
        fb.set_row_spacing(8)
        fb.set_hexpand(True)
        return fb

    def _add_button(self, container: Gtk.FlowBox, label: str, cb):
        btn = Gtk.Button(label=label)
        btn.set_margin_top(2)
        btn.set_margin_bottom(2)
        btn.set_hexpand(True)  # allows buttons to grow / shrink with window
        btn.connect("clicked", cb)
        container.append(btn)

    # ───────── directory handlers ─────────
    def input_folder(self, *_):
        click.launch(input_folder)

    def regex_folder(self, *_):
        click.launch(regexes_folder)

    def text_file_folder(self, *_):
        click.launch(text_record_folder)

    def toc_file(self, *_):
        click.launch(toc_file)

    def completed_records(self, *_):
        click.launch(completed_records_folder)

    # ───────── progress updaters ─────────
    def update_progress(self, frac):
        GLib.idle_add(self.progress_bar.set_fraction, frac)
        GLib.idle_add(
            self.progress_bar.set_text, f"Creating TOC File: {int(frac * 100)}%"
        )

    def update_page_progress(self, frac):
        GLib.idle_add(self.page_progress_bar.set_fraction, frac)
        GLib.idle_add(
            self.page_progress_bar.set_text,
            f"Applying Bookmarks: {int(frac * 100)}%",
        )

    # ───────── actions (each runs in its own thread) ─────────
    def CreateTOC(self, *_):
        threading.Thread(target=self._run_create_toc, daemon=True).start()

    def _run_create_toc(self):
        toc_creator.create_toc(
            text_record_folder,
            input_folder,
            combined_pdf_path,
            toc_file,
            regexes_folder,
            self.update_progress,
        )
        GLib.idle_add(click.launch, toc_file)

    def BookMark(self, *_):
        threading.Thread(target=self._run_pdfoutline, daemon=True).start()

    def _run_pdfoutline(self):
        pdfoutline(
            combined_pdf_path,
            toc_file,
            completed_record_pdf,
            gs="gs",
            update_progress=self.update_page_progress,
        )
        GLib.idle_add(click.launch, completed_record_pdf)

    def RunBoth(self, *_):
        threading.Thread(target=self._run_both, daemon=True).start()

    def _run_both(self):
        toc_creator.create_toc(
            text_record_folder,
            input_folder,
            combined_pdf_path,
            toc_file,
            regexes_folder,
            self.update_progress,
        )
        pdfoutline(
            combined_pdf_path,
            toc_file,
            completed_record_pdf,
            gs="gs",
            update_progress=self.update_page_progress,
        )
        GLib.idle_add(click.launch, completed_record_pdf)

    # ───────── quit helper ─────────
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

