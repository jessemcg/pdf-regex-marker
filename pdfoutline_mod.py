#!/usr/bin/python3

import re
import subprocess
import tempfile, os
from typing import List
from gi.repository import Gtk, GLib

# Adapted from pdfoutline (https://github.com/yutayamamoto/pdfoutline)
# Adobe pdfMark Reference
# https://opensource.adobe.com/dc-acrobat-sdk-docs/acrobatsdk/pdfs/acrobatsdk_pdfmark.pdf

# in toc file, you must close the parenthesis()!! otherwise, gs fails.
class Entry:
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
    tab = ""    # indentation character(s) evaluated and assigned to this later
    lines = toc.split('\n')
    cur_entry = [[]]    # current entries by depth
    offset = 0

    # add whitespace characters to tab
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

        line = line.split('#')[0].strip()

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

def pdfoutline(inpdf: str, tocfilename: str, outpdf: str, gs='gs', update_progress=None):
    with open(tocfilename) as f:
        toc = f.read()
        gs_command = elist_to_gs(toc_to_elist(toc))
        
    tmp = tempfile.NamedTemporaryFile(mode = 'w', delete=False)
    tmp.write(gs_command)
    tmp.close()

    process = subprocess.Popen(
        [gs, '-dNEWPDF=false', '-o', outpdf, '-sDEVICE=pdfwrite', tmp.name, '-f', inpdf],
        stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)

    totalPage = 0
    currentPage = 0
    for line in process.stdout:
        if not totalPage:
            tot = re.findall(r'Processing pages 1 through (\d+)', line)
            if tot:
                totalPage = int(tot[0])
        else:
            currentPageMatch = re.findall(r'Page (\d+)', line.strip())
            if currentPageMatch:
                currentPage = int(currentPageMatch[0])
        if totalPage and currentPage and update_progress:
            progress = currentPage / totalPage
            update_progress(progress)

    process.stdout.close()
    process.wait()

    os.unlink(tmp.name)
