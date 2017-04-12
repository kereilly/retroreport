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

## parse the epected date format from google sheets YYYY MMM DD
def parse_date(string, v = 1):

    ## split the string into a list seperated by spaces
    elements = string.split()

    ## touble shooting
    if v >= 3:

        print "\nraw string sent to parse_date:\n " + string
        print "String broken into elements: \n"
        print elements

    dictdate = {'year': elements[0], 'month': 11, 'day': elements[2]} ## make our dictionary
    if elements[1].lower() in ("jan", "january"):
        dictdate['month'] = "01"
    elif elements[1].lower() in ("feb", "february"):
        dictdate['month'] = "02"
    elif elements[1].lower() in ("mar", "march"):
        dictdate['month'] = "03"
    elif elements[1].lower() in ("apr", "april"):
        dictdate['month'] = "04"
    elif elements[1].lower() == "may":
        dictdate['month'] = "05"
    elif elements[1].lower() in ("jun", "june"):
        dictdate['month'] = "06"
    elif elements[1].lower() in ("jul", "july"):
        dictdate['month'] = "07"
    elif elements[1].lower() in ("aug", "august"):
        dictdate['month'] = "08"
    elif elements[1].lower() in ("sep", "september"):
        dictdate['month'] = "09"
    elif elements[1].lower() in ("oct", "october"):
        dictdate['month'] = "10"
    elif elements[1].lower() in ("nov", "november"):
        dictdate['month'] = "11"
    elif elements[1].lower() in ("dec", "december"):
        dictdate['month'] = "12"
    else:                       ## text not standard month. Make it unknown
        dictdate['month'] = "11"

    if v >= 3:
        print dictdate

    return dictdate


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
    jobs = csv_process(path, verbosity)
    print str(len(jobs)) + " jobs to process"

    downloaded = [] # create array to hold results of the sucessful download
    failed = [] # create array to hold the failed attempts

    # Loop through the list and process each job
    for job in jobs:
        ## parse date field
        if job[3] == "":
            if verbosity >= 2:
                print "No date entry. Putting in 1111_11_11"
            textdate = "11 NOV 1111"
        else:
            textdate = job[3]

        dictdates = parse_date(textdate)

        file_name = job[2]
        url = job[6]
        print "Raw date is: " + job[3]
        print dictdates
        print ""






if __name__ == "__main__":
    main();
