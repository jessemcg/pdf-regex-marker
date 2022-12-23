#!/usr/bin/python3

import re
import click
import pdftotext
import PyPDF2
from PyPDF2 import PdfFileMerger
import os
import shutil
import sys
import subprocess
import tempfile, os, sys
import PySimpleGUI as sg

# PysimpleGUI Layout
sg.theme('Topanga')
layout = [  [sg.Text('FOLDERS AND FILES')],
            [sg.Button('Input Folder', size=(25,1)),sg.Button('REGEX Folder', size=(25,1))],
            [sg.Button('Text File Folder', size=(25,1)),sg.Button('TOC File', size=(25,1))],
            [sg.Text('')],
            [sg.Text('PROCESSING')],
            [sg.Button('Run', size=(25,1)),sg.Button('Redo (after TOC edit)', size=(25,1))],
            [sg.Text('creating table of contents')],
            [sg.ProgressBar(100, orientation='h', size=(51.5, 20), key='text_file_prog')],
            [sg.Text('applying bookmarks')],
            [sg.ProgressBar(100, orientation='h', size=(51.5, 20), key='outline_prog')],
            [sg.Text('')],
            [sg.Button('Completed Records', size=(25,1)),sg.Button('Exit')]]

# Create the main window
window = sg.Window('PDF Regex Marker', layout, font="_")

# Create variable for two progress bars
text_file_prog = window['text_file_prog']
outline_prog = window['outline_prog']

# Make required folders unless they already exist
if not os.path.exists('input_folder'):
    os.makedirs('input_folder')
if not os.path.exists('regexes'):
    os.makedirs('regexes')
if not os.path.exists('completed_records'):
    os.makedirs('completed_records')

# Function that creates the table of contents by running regular expression against
# each page of the record that has been converted into text files 
def create_toc():
    # create temp folder with text_record folder; replace old one if already exists
    if os.path.exists ('temp\\text_record'):
        shutil.rmtree('temp\\text_record')
    os.makedirs('temp\\text_record')

    # take pdf files from input_folder folder and combine them into combined.pdf
    merger = PdfFileMerger()
    path_to_record = r'input_folder/'
    for root, dirs, file_names in os.walk(path_to_record):
        for file_name in file_names:
            merger.append(path_to_record + file_name)  
            
    # write combined pdf into temp file
    merger.write('temp\\combined.pdf')
    merger.close() 

    # open combined pdf file
    with open('temp\\combined.pdf', 'rb') as f:
        pdf = pdftotext.PDF(f,physical=True)

    # create separate text file for each pdf page and place them in text_record folder
    i = 1       # variable to iterate the file names
    j = 0       # variable to iterate the pdf pages
    z = 0       # variable to iterate progress bar
    # progress bar stuff
    file = open('temp\\combined.pdf', 'rb')
    readpdf = PyPDF2.PdfFileReader(file)
    totalpages = readpdf.numPages
    prog_i = 100/totalpages
    # progress bar stuff
    for x in pdf:
        i_str = str(i).zfill(4)
        j_str = str(j)
        filename = 'temp\\text_record\\' + i_str + '.txt'
        f = open(filename,'w', encoding='utf8')
        f.write(pdf[j])
        f.close()
        i = i+1
        j = j+1
        # progress bar
        z = z+prog_i
        text_file_prog.UpdateBar(z)
        
    # replace the old table of contents file, create one if not there
    if os.path.exists('toc.txt'):
        os.remove('toc.txt')
        fp = open('toc.txt', 'x')
        fp.close()
    if not os.path.exists('toc.txt'):
        fp = open('toc.txt', 'x')
        fp.close()

    # open and iterate through the regex list in regex file
    for regex_file in os.listdir('regexes'):
        with open('regexes/' + regex_file, encoding='utf8') as f:
            f = f.read().splitlines()                   # lose the \n character
            f = filter(str.rstrip, f)                   # ignore empty lines
            y = [re.compile(line) for line in f]        # create compiled list of regexes
            d = regex_file.replace(".txt","")           # lose the .txt
            toc_file = open('toc.txt', 'a')
            toc_file.write(d + ' 0001' + '\n')

        # open and read all text files in the text_record folder
        for record_file in os.listdir('temp/text_record'):
            with open('temp/text_record/' + record_file, encoding='utf8') as f:
                x = f.read()
            
            # run each regex against each text file in the record
            for regex in y:
                a = regex.search(x)
                # if match, print file name (also the page number) and matched word(s)
                if a:
                    record_file = record_file.replace(".txt","")    # lose the .txt
                    toc_file = open('toc.txt', 'a')
                    regex_hit = f'\t {a.group()} {record_file} \n'
                    toc_file.write(regex_hit)

# this is pdfoutline (https://github.com/yutayamamoto/pdfoutline)
# original comments included; only modified to get rid of command line progress bar and command line arguments

# Adobe pdfMark Reference
# https://opensource.adobe.com/dc-acrobat-sdk-docs/acrobatsdk/pdfs/acrobatsdk_pdfmark.pdf
# in toc file, you must close the parenthesis()!! otherwise, gs fails.

class Entry():

    def __init__(self, name, page, children):
        self.name = name
        self.page = page
        self.children = children # Entry list

    def pritty_print(self, depth):
        print(depth * '  ' + self.name + ':' + str(self.page))
        for c in self.children:
            c.pritty_print(depth+1)
            
# Parse the start of the line for whitespace characters and return "tab";
# should only be called once on first occurrence of an indent while tab == ""
def parse_tab(line):
    tab = ""

    # add whitespace characters to tab
    for ch in line:
        if (ch.isspace()):
            tab += ch
        else:
            break

    return tab

def toc_to_elist(toc):

    tab = "" # indentation character(s) evaluated and assigned to this later
    lines = toc.split('\n')
    cur_entry = [[]] # current entries by depth
    offset = 0

    for line in lines:

        # if indentation style hasn't been evaluated yet and the line starts
        # with a whitespace character, assume its an indent and assign all the
        # leading whitespace to tab
        if ((tab == "") and (line != "") and (line[0].isspace())):
            tab = parse_tab(line)

        depth = 0

        # determine depth level of indent
        if (tab != ""):
            # find length of leading whitespace in string
            ws_len = 0
            for ch in line:
                if (ch.isspace()):
                    ws_len += 1
                else:
                    break

            # count indent level up to first non-whitespace character;
            # allows for "indents" to appear inside section titles e.g. if an
            # indent level of a single space was chosen
            depth = line.count(tab, 0, ws_len)

        line = line.split('#')[0].strip() # strip comments and white spaces

        if not line:
            continue

        if line[0] == '+':
            offset += int(line[1:])
            continue

        if line[0] == '-':
            offset -= int(line[1:])
            continue

        try:
            (name, page) = re.findall(r'(.*) (\d+)$', line)[0]
            page = int(page) + offset
            cur_entry = cur_entry[:depth+1] + [[]]
            cur_entry[depth].append(Entry(name, page, cur_entry[depth+1]))

        except:
            # todo display line number
            print('syntax error in toc-file. line:\n' + line)
            exit(1)

    return cur_entry[0]

def elist_to_gs(elist):

    def rec_elist_to_gslist(elist):
        gs_list = []
        for entry in elist:
            gs_list.append("[/Page %d /View [/XYZ null null null] /Title <%s> /Count %d /OUT pdfmark" \
                    % (entry.page, entry.name.encode("utf-16").hex(), len(entry.children)))
            gs_list += rec_elist_to_gslist(entry.children)
        return gs_list

    return '\n'.join(rec_elist_to_gslist(elist))

def pdfoutline(inpdf, tocfilename, outpdf, gs='gs'):

    with open(tocfilename) as f:
        toc = f.read()
        gs_command = elist_to_gs(toc_to_elist(toc))

    tmp = tempfile.NamedTemporaryFile(mode = 'w', delete=False)
    tmp.write(gs_command)
    tmp.close()

    process = subprocess.Popen(\
        ['gswin64c.exe', '-dNEWPDF=false', '-o', outpdf, '-sDEVICE=pdfwrite', tmp.name, '-f', inpdf],\
        stdout=subprocess.PIPE)

    totalPage = 0
    z = 0       # variable to iterate progress bar
    for line in process.stdout:
        # progress bar stuff
        file = open('temp\\combined.pdf', 'rb')
        readpdf = PyPDF2.PdfFileReader(file)
        totalpages = readpdf.numPages
        prog_i = 100/totalpages
        # progress bar stuff
        tot = re.findall(r'Processing pages 1 through (\d+)', line.decode('ascii'))
        if tot:
            totalPage = int(tot[0])
            break

    for line in process.stdout:
        currentPage = re.findall(r'Page (\d+)', line.decode('ascii').strip())
        if currentPage:
            # progress bar
            z = z+prog_i
            outline_prog.UpdateBar(z)

    os.unlink(tmp.name)
    
# The loop that is controlled by the gui
while True:
    event, values = window.read()
    # open input folder with button
    if event == 'Input Folder':
        click.launch('input_folder')
    # open regexes folder with button
    if event == 'REGEX Folder':
        click.launch('regexes')
    # open text records folder with button
    if event == 'Text File Folder':
        click.launch('temp\\text_record')
    # open table of contents file with button
    if event == 'TOC File':
        click.launch('toc.txt')
    # open completed records folder with button
    if event == 'Completed Records':
        click.launch('completed_records')
    # run everything from start to finish
    if event == 'Run':
        create_toc()
        pdfoutline('temp\\combined.pdf', 'toc.txt', 'completed_records\\completed_record.pdf')
        click.launch('completed_records\\completed_record.pdf')
    # after editing toc file, just run the part that creates the bookmarks
    if event == 'Redo (after TOC edit)':
        pdfoutline('temp\\combined.pdf', 'toc.txt', 'completed_records\\redo_completed_record.pdf')
        click.launch('completed_records\\redo_completed_record.pdf')
    # See if user wants to quit or window was closed
    if event == sg.WINDOW_CLOSED or event == 'Exit':
        break
