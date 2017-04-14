#!/usr/bin/env python

## This script is meant to batch download archival from Retro Reports Archival Tracker form.
## https://github.com/kereilly/retroreport

## stuff to import
import csv
import argparse
import os.path
import parsedatetime
from retrosupport import process
from retrosupport.process import volume_result
from retrosupport.process import datetimeFromString

def set_argparse():


    # Start things off using pythons argparse. get user input and give help information
    parser = argparse.ArgumentParser(
        description="Tracker Batch eMAM Downloader Version .1",
        epilog="Please do not feed the Media Manager"
    )


    # Group arguments for batch download
    group_batch = parser.add_argument_group("Batch Download", "Arguments for Batch Downloading")
    group_batch.add_argument("-i", "--input", type=str,
                             help="Specify a CSV file for batch download")
    group_batch.add_argument("-m", "--multi_thread", action="store_true", help="Enable multi-threaded downloads")
    group_batch.add_argument("-d", "--output_directory", type=str,
                             help="Specify output directory to save to. Should already exist "
                                  "I won't make the Directory for you. Or maybe I will. Hmmmm.")
    group_batch.add_argument("-r", "--project_id", type=str,
                             help="Override the Google Sheets provided project ID")
    # now regular arguments
    parser.add_argument("-v", "--verbosity", type=int, default=1, choices=[0, 1, 2, 3],
                        help="Increase, 2, or decrease, 0, the level of output. 3 is debug mode. Default is 1")
    parser.add_argument("-p", "--premiere", action="store_true", help="Convert media automatically if it is "
                            "not premiere compatible")

    # have argparse do its thing
    args = parser.parse_args()

    # pack up what we need to bring back to main
    pack = (parser, args)
    return pack

def csv_process(path, verbosity = 1):

    # Open the csv file to work on
    if verbosity >= 2:
        print "Attempting to open csv file at: " + path
    csv_file = process.open_file(path, "r")


    if csv_file == volume_result.not_found:
        print "No file found at: " + path
        print "Please find your csv file and try again"
        exit()
    else:
        reader = csv.reader(csv_file)
        jobs_list = list(reader)        # convert reader to list
        if verbosity >= 3:
            print "output of CSV file:"
            for line in jobs_list:
                print line
            print ""
        return jobs_list


    ## check to see if the user inputed good stuff

def check_args(args):

    # check and make sure csv file is good
    if args.input == None:
        print "You did not specify a CSV file"
        print "Please Specify a CSV file with the -i switch"
        exit() # with no csv file there is nothing to do

    elif not os.path.isfile(args.input):
        print "The file you specified at: " + args.input + " is not valid"
        print "Please specify a valid csv file"
        exit()  # with no csv file there is nothing to do


    # check and make sure output directory is good
    if args.output_directory == None:
        print "You didn't specify a directory to save to"
        print "Please specifiy a valid directory to save to with the -d swtich"
        exit() # Cuz we have nowhere to put anything
    elif not os.path.isdir(args.output_directory):
        print "The directory you specified to save to does not exist: " \
              + args.output_directory + " please specifiy a valid directory to save to"
        exit()  # Cuz we have nowhere to put anything

def month_text_to_number(string):

    if string.lower() in ("jan", "january"):
        string = "01"
    elif string.lower() in ("feb", "february"):
        string = "02"
    elif string.lower() in ("mar", "march"):
        string = "03"
    elif string.lower() in ("apr", "april"):
        string = "04"
    elif string.lower() == "may":
        string = "05"
    elif string.lower() in ("jun", "june"):
        string = "06"
    elif string.lower() in ("jul", "july"):
        string = "07"
    elif string.lower() in ("aug", "august"):
        string = "08"
    elif string.lower() in ("sep", "september"):
        string = "09"
    elif string.lower() in ("oct", "october"):
        string = "10"
    elif string.lower() in ("nov", "november"):
        string = "11"
    elif string.lower() in ("dec", "december"):
        string = "12"
    else:  ## text not standard month. Make it unknown
        string = "11"

    return string

## parse the epected date format from google sheets YYYY MMM DD
def parse_date(string, v = 1):

    ## split the string into a list seperated by spaces
    elements = string.split()

    ## touble shooting
    if v >= 3:
        print "\nraw string sent to parse_date:\n " + string
        print "String broken into elements:"
        print elements

    months = ["dec", "december", "nov", "november", "oct", "october", "sep", "september",
              "aug", "august", "jul", "july", "jun", "june", "may", "apr", "april",
              "mar", "march", "feb", "february", "jan", "january"]

    dictdate = {'year': "1111", 'month': "11", 'day': "11"} # create date dictionary. seed with our "unknown date"


    ## go through possible date formats
    if len(elements) == 3:      # what we should get
        dictdate['year'] = elements[0]
        dictdate['month'] = month_text_to_number(elements[1])
        dictdate['day'] = elements[2]
    elif len(elements) == 1:    # just a year maybe?
        if len(elements[0]) == 4:
            dictdate['year'] = elements[0]
    elif len(elements) == 2:    # month and year?
        for item in elements:
            if len(item) == 4:
                dictdate['year'] = item
            # check for months
            if item in months:
                dictdate['month'] = month_text_to_number(item)

            if item.isdigit():
                if int(item) <= 12: # can't b more than 12. value will be ignored if so
                    if len(item) == 1:
                        item = "0" + item   # month is only 1 digit pad with string
                    dictdate['month'] = item

    if v >= 3:
        print dictdate

    return dictdate

## replace spaces with '_' and '/' with '-' and take out quotes
def format_string(string):

    return_string = string.replace(" ", "_")
    return_string = return_string.replace("/", "-")
    return_string = return_string.replace('"', "")
    return_string = return_string.replace("'", "")
    return_string = return_string.replace(';', "")
    return_string = return_string.replace(",", "")

    return return_string

## unelegantly create our standard asset label from the number
def pad_asset(asset, v = 1):

    if len(asset) == 1:
        return_asset = "A00" + asset
        if v >=3:
            print "\nOriginal Asset Variable: " + asset
            print "Modified Asset Variable: " + return_asset
    elif len(asset) == 2:
        return_asset = "A0" + asset
        if v >=3:
            print "\nOriginal Asset Variable: " + asset
            print "Modified Asset Variable: " + return_asset
    elif len(asset) == 3:
        return_asset = "A" + asset
        if v >=3:
            print "\nOriginal Asset Variable: " + asset
            print "Modified Asset Variable: " + return_asset
    else:
        return_asset = "A1000"

    return return_asset

def create_metadata(job, project_id, v = 1):


    ## pad asset number
    asset_number = pad_asset(job[0], v)
    ## parse date field
    if job[3] == "":
        if v >= 2:
            print "No date entry. Putting in 1111_11_11"  ## this is the entry meaning we don't know the date
        textdate = "1111 NOV 11"
    else:
        textdate = job[3]
    dictdate = parse_date(textdate)

    ## build filename
    file_name = project_id + "_" + asset_number + "_" + dictdate['year'] + "_" + dictdate['month']\
                + "_" + dictdate['day'] + "_" + format_string(job[1]) + "_" + format_string(job[2])

    ## create our dictionary
    metadata = {'file_name':file_name, 'date':dictdate, 'source':job[1], 'source_id':job[2], 'description':job[4],
                'link':job[5], 'in':job[6], 'out':job[7], 'notes':job[8], 'copy_holder':job[9], 'license_status':job[10],
                'copyright_status':job[11], 'project_id':project_id, 'asset_number':job[0], 'formated_asset_number': asset_number}

    return metadata

def main():

    print ""  # a nice blank space after the user puts in all the input
    # get arguments set up
    unpack = set_argparse()  # returns list of parsed arguments and the parser itself
    parser = unpack[0]  # unpack the parser
    args = unpack[1]  # unpack the parsed args

    check_args(args)
    verbosity = args.verbosity
    path = args.input

    # Multithreading not supported yet. Warn user if enabled
    if args.multi_thread:
        print "You enabled Multithreading. At this point it is not supported but hopefully soon"
        print "The -m flag will be ignored\n"


    ## put all our jobs from the csv file into an array

    csv_dump = csv_process(path, verbosity) # ingest the csv file
    csv_first_pass = [] # create our list to put jobs in

    ## check the project ID
    if args.project_id == None:
        project_id = csv_dump[0][0] # extract the project ID number
        if verbosity >= 3:
            print "Using google sheet provided project id: " + project_id
    else:
        project_id = args.project_id
        if verbosity >= 3:
            print "Using user provided provided project id: " + project_id

    if project_id == "unknown":
        print "The Google Sheet JavaScript did not provide a project ID"
        print "Specify your own project ID with the -r flag. Downloader will not continue"
        exit()
    ## copy the rest of the list, everything except first element
    after_first_item = False
    for item in csv_dump:
        if after_first_item:
            csv_first_pass.append(item)
        after_first_item = True # need to mark we passed the first item

    print str(len(csv_first_pass)) + " jobs to process"

    # create job tuple
    jobs = []
    # Loop through the list and format each job
    for item in csv_first_pass:

        # put all our meta data in a nice dictionary
        metadata = create_metadata(item, project_id, verbosity)
        print "File name for asset " + item[0] + " is: " + metadata['file_name']
        jobs.append(metadata)

    for job in jobs:
        print job









if __name__ == "__main__":
    main();
