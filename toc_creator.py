#!/usr/bin/python3

import os
import shutil
import pdftotext
import PyPDF2
from gi.repository import GLib
import re

def create_toc(text_record_folder, input_folder, combined_pdf_path, toc_file, regexes_folder, update_progress=None):
    # create temp folder with text_record folder; replace old one if already exists
    if os.path.exists(text_record_folder):
        shutil.rmtree(text_record_folder)
    os.makedirs(text_record_folder)
    
    # merge all pdfs in the input folder
    pdf_merger = PyPDF2.PdfMerger()

    # get a list of all PDF files in the directory
    pdf_files = [f for f in os.listdir(input_folder) if f.endswith('.pdf')]
    pdf_files.sort()  # Sort the files to maintain order
    
    for pdf in pdf_files:
        with open(os.path.join(input_folder, pdf), 'rb') as file:
            pdf_merger.append(file)

    with open(combined_pdf_path, 'wb') as output_file:
        pdf_merger.write(combined_pdf_path)

    # open combined pdf file
    with open(combined_pdf_path, 'rb') as f:
        pdf = pdftotext.PDF(f, physical=True)
        total_pages = len(pdf)

    # create separate text file for each pdf page and place them in text_record folder
    for page_number, page_content in enumerate(pdf, start=1):
        filename = os.path.join(text_record_folder, f'{page_number:04}.txt')
        with open(filename, 'w') as f:
            f.write(page_content)
        if update_progress:
            update_progress(page_number / total_pages)

    # replace the old table of contents file, create one if not there
    if os.path.exists(toc_file):
        os.remove(toc_file)
    with open(toc_file, 'w'): pass

    # open and iterate through the regex list in regex file
    for regex_file in os.listdir(regexes_folder):
        with open(os.path.join(regexes_folder, regex_file), encoding='utf8') as f:
            f = f.read().splitlines()                  # lose the \n character
            f = filter(str.rstrip, f)                  # ignore empty lines
            y = [re.compile(line) for line in f]       # create compiled list of regexes
            d = regex_file.replace(".txt","")          # lose the .txt
            with open(toc_file, 'a') as toc_object:
                toc_object.write(d + ' 0001' + '\n')

        # open and read all text files in the text_record folder
        for record_file in sorted(os.listdir(text_record_folder), key=lambda x: int(x.split('.')[0])):
            with open(os.path.join(text_record_folder, record_file)) as f:
                x = f.read()
            # run each regex against each text file in the record
            for regex in y:
                a = regex.search(x)
                # if match, print file name (also the page number) and matched word(s)
                if a:
                    record_file = record_file.replace(".txt","")   # lose the .txt
                    with open(toc_file, 'a') as toc_object:
                        regex_hit = f'\t{a.group()} {record_file}\n'
                        toc_object.write(regex_hit)
                        
    # add a new blank line to the end of the toc.txt so awk will work)
    with open(toc_file, 'a') as toc_object:
        toc_object.write('\n')
        
    # optionally modify the toc file with a bash script
    #if os.path.exists("bash_script.sh"):
        #os.system("bash bash_script.sh")


