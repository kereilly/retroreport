#!/usr/bin/env python
# encoding: utf-8
from __future__ import unicode_literals
# This script is meant to batch download archival from Retro Reports Archival Tracker form.
# https://github.com/kereilly/retroreport

# stuff to import
import csv
import argparse
import os.path
import xlsxwriter
import retrosupport
import time
import string
import sys
from retrosupport import process
from retrosupport import media
from retrosupport import locate
from retrosupport import retro_dl
from retrosupport import emamsidecar

# for unicode type issues when reading the csv file
reload(sys)
sys.setdefaultencoding('utf8')


def set_argparse():
    # Start things off using pythons argparse. get user input and give help information
    parser = argparse.ArgumentParser(
        description="Tracker Batch eMAM Downloader Version 1.0.2",
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
    group_batch.add_argument("-l", "--later", "--later", action="store_true",
                             help="Don't download any assets. Create xml for later download")
    group_batch.add_argument("-e", "--extension", type=str,
                             help="Overide '.mov' extension for assets not downloaded")
    group_batch.add_argument("-f", "--force_extension", action="store_true",
                             help="force custom extension even if url found in extension library")
    group_batch.add_argument("-r", "--project_id", type=str,
                             help="Override the Google Sheets provided project ID")
    # now regular arguments
    parser.add_argument("-v", "--verbosity", type=int, default=1, choices=[0, 1, 2, 3],
                        help="Increase, 2, or decrease, 0, the level of output. 3 is debug mode. Default is 1")
    parser.add_argument("-p", "--premiere", action="store_true", help="Convert media automatically if it is "
                                                                      "not premiere compatible")

    parser.add_argument("-g", "--google_screener", action="store_true", help="Create mp4's for the google drive")

    parser.add_argument("-o", "--xml_ingest", type=int, choices=[1, 2, 3, 4], help="Raid location usage")

    parser.add_argument("-c", "--category", type=str, help="Create custom category. Good for loading in archival"
                                                           "after project has started")

    parser.add_argument("-x", "--screener_location", type=str, help="Overide where the screeners are made")

    # have argparse do its thing
    args = parser.parse_args()

    # pack up what we need to bring back to main
    pack = (parser, args)
    return pack


def csv_process(path, verbosity=1):
    # Open the csv file to work on
    if verbosity >= 2:
        print ("Attempting to open csv file at: " + path)
    csv_file = process.open_file(path, "r")

    if csv_file == retrosupport.process.volume_result.not_found:
        print ("No file found at: " + path)
        print ("Please find your csv file and try again")
        exit()
    else:
        reader = csv.reader(csv_file)
        jobs_list = list(reader)  # convert reader to list

        # clean any strange unicode characters
        jobs_list_clean = []
        job_clean = []

        for job in jobs_list:
            for text in job:
                retrosupport.process.clean_latin1(text)
                job_clean.append(text)
            jobs_list_clean.append(job_clean)
            job_clean = []
        if verbosity >= 3:
            print ("output of CSV file:")
            for item in jobs_list_clean:
                print (item)
            print ("")
        return jobs_list


# check to see if the user input good stuff
def check_args(args):
    # check and make sure csv file is good
    if args.input is None:
        print ("You did not specify a CSV file")
        print ("Please Specify a CSV file with the -i switch")
        exit()  # with no csv file there is nothing to do

    elif not os.path.isfile(args.input):
        print ("The file you specified at: " + args.input + " is not valid")
        print ("Please specify a valid csv file")
        exit()  # with no csv file there is nothing to do

    # check and make sure output directory is good
    if args.output_directory is None:
        print ("You didn't specify a directory to save to")
        print ("Please specify a valid directory to save to with the -d switch")
        exit()  # Cuz we have nowhere to put anything
    elif not os.path.isdir(args.output_directory):
        print ("The directory you specified to save to does not exist: "
               + args.output_directory + " please specify a valid directory to save to")
        exit()  # Cuz we have nowhere to put anything


#  Check and see if a valid time code was entered in the tracker
def subtime_valid(subtime_in, subtime_out, v=1):
    subtime_in = subtime_in.replace(':', '')
    subtime_out = subtime_out.replace(':', '')

    if subtime_in == "" or subtime_out == "":
        if v >= 2:
            print ("subclip time set blank")
        return False
    if subtime_in.isdigit() and subtime_out.isdigit():
        time_in = int(subtime_in)
        time_out = int(subtime_out)

        # check to see if out point comes before in
        if time_in > time_out:
            if v >= 2:
                print ("Time out starts before time in")
            return False
        else:
            if v >= 2:
                print ("subclip time is in correct format")
            return True
    else:
        if v >= 2:
            print ("subclip time is in incorrect format")
        return False


#  Pad the time code for sublclips
def pad_timecode(time_code):
    if time_code != "":
        # no hour placement, pad with 0's
        if time_code[0] == ":":
            time_code = "00" + time_code

    time_code = time_code + ":00"  # add frames
    return time_code


#  Formats time code string for eMAM compatibility
def subclip(job, v=1):

    if subtime_valid(job['first_in'], job['first_out'], v):

        if job['first_label'] == "":  # Make a label if one doesn't exist
            job['first_label'] = "Subclip 1"
        # Pad our timecodes
        job['first_in'] = pad_timecode(job['first_in'])
        job['first_out'] = pad_timecode(job['first_out'])
    else:
        if v >= 1:
            print("Clearing first set of sublclip feilds")
        job['first_in'] = ""
        job['first_out'] = ""
        job['first_label'] = ""

    if subtime_valid(job['second_in'], job['second_out'], v):

        if job['second_label'] == "":  # Make a label if one doesn't exist
            job['second_label'] = "Subclip 2"
        # Pad our timecodes
        job['second_in'] = pad_timecode(job['second_in'])
        job['second_out'] = pad_timecode(job['second_out'])
    else:
        if v >= 1:
            print("Clearing second set of sublclip feilds")
        job['second_in'] = ""
        job['second_out'] = ""
        job['second_label'] = ""

    return job


# make sure the archival goes into the right master archival category based on date
def year_categories(year, decade, v=1):

    year_inf = [False, False, False]  # place holder to check req for year. 0 is empty, 1 is digit, 2 is 4 characters
    category_paths = []  # a holder for all our paths

    category_path = "Archival/"  # Root of master archival category
    if year != "":
        year_inf[0] = True  # check to see if its an integer
        if year.isdigit():
            year_inf[1] = True
        else:
            if v >= 2:
                print("Year is not correct format. Not a number")
        if len(year) == 4:  # check to see if the integer is 4 digits long
            year_inf[2] = True
        else:
            if v >= 2:
                print("Year is not in correct format. It is not a 4 digit number")
    else:
        if v >= 2:
            print("This asset has no year entered")

    if year_inf[0] and year_inf[1] and year_inf[2]:
        int_year = int(year)  # convert year to integer so we can compare
        if int_year < 1920:
            category_path = category_path + "1919-Under"
        elif int_year < 1930:
            category_path = category_path + "1920-1929/"
            if int_year < 1925:
                category_path = category_path + "1920-1924/" + str(year)
            else:
                category_path = category_path + "1925-1929/" + str(year)
        elif int_year < 1940:
            category_path = category_path + "1930-1939/"
            if int_year < 1935:
                category_path = category_path + "1930-1934/" + str(year)
            else:
                category_path = category_path + "1935-1939/" + str(year)
        elif int_year < 1950:
            category_path = category_path + "1940-1949/"
            if int_year < 1945:
                category_path = category_path + "1940-1944/" + str(year)
            else:
                category_path = category_path + "1945-1949/" + str(year)
        elif int_year < 1960:
            category_path = category_path + "1950-1959/"
            if int_year < 1955:
                category_path = category_path + "1950-1954/" + str(year)
            else:
                category_path = category_path + "1955-1959/" + str(year)
        elif int_year < 1970:
            category_path = category_path + "1960-1969/"
            if int_year < 1965:
                category_path = category_path + "1960-1964/" + str(year)
            else:
                category_path = category_path + "1965-1969/" + str(year)
        elif int_year < 1980:
            category_path = category_path + "1970-1979/"
            if int_year < 1975:
                category_path = category_path + "1970-1974/" + str(year)
            else:
                category_path = category_path + "1975-1979/" + str(year)
        elif int_year < 1990:
            category_path = category_path + "1980-1989/"
            if int_year < 1985:
                category_path = category_path + "1980-1984/" + str(year)
            else:
                category_path = category_path + "1985-1989/" + str(year)
        elif int_year < 2000:
            category_path = category_path + "1990-1999/"
            if int_year < 1995:
                category_path = category_path + "1990-1994/" + str(year)
            else:
                category_path = category_path + "1995-1999/" + str(year)
        elif int_year < 2010:
            category_path = category_path + "2000-2009/"
            if int_year < 2005:
                category_path = category_path + "2000-2004/" + str(year)
            else:
                category_path = category_path + "2005-2009/" + str(year)
        elif int_year < 2020:
            category_path = category_path + "2010-2019/"
            if int_year < 2015:
                category_path = category_path + "2010-2014/" + str(year)
            else:
                category_path = category_path + "2015-2019/" + str(year)
        elif int_year < 2030:
            category_path = category_path + "2010-2019/"
            if int_year < 2025:
                category_path = category_path + "2020-2024/" + str(year)
            else:
                category_path = category_path + "2025-2029/" + str(year)
        elif int_year < 2040:
            category_path = category_path + "2010-2019/"
            if int_year < 2035:
                category_path = category_path + "2030-2034/" + str(year)
            else:
                category_path = category_path + "2035-2039/" + str(year)
        else:
            category_path = ""
            if v >= 1:
                print("Error. Year is out of range for the master archival category")

        category_paths.append(category_path)

    # take care of decade
    elif decade != "":
        if "1920" in decade:
            category_paths.append("Archival/1920-1929-Decade")
        if "1930" in decade:
            category_paths.append("Archival/1930-1939-Decade")
        if "1940" in decade:
            category_paths.append("Archival/1940-1949/Decade")
        if "1950" in decade:
            category_paths.append("Archival/1950-1959/Decade")
        if "1960" in decade:
            category_paths.append("Archival/1960-1969/Decade")
        if "1970" in decade:
            category_paths.append("Archival/1970-1979/Decade")
        if "1980" in decade:
            category_paths.append("Archival/1980-1989/Decade")
        if "1990" in decade:
            category_paths.append("Archival/1990-1999/Decade")
        if "2000" in decade:
            category_paths.append("Archival/2000-2009/Decade")
        if "2010" in decade:
            category_paths.append("Archival/2010-2019/Decade")
        if "2020" in decade:
            category_paths.append("Archival/2020-2029/Decade")
        if "2030" in decade:
            category_paths.append("Archival/2030-2039/Decade")
    else:
        if v >= 2:
            print("No decade defined for this asset")
    return category_paths


# Take copyright status and put in abbreviation
def copyright_labler(text):
    clean_text = retrosupport.process.filename_format(text)
    if clean_text.lower() == "fair_use":
        return "_FU"
    elif clean_text.lower() == "fair_use_pending":
        return "_FUP"
    elif clean_text.lower() == "public_domain":
        return "_PD"
    elif clean_text.lower() == "public_domain_pending":
        return "_PDPend"
    elif clean_text.lower() == "royalty_free":
        return "_RF"
    elif clean_text.lower() == "license":
        return "_Lic"
    elif clean_text.lower() == "license_personal":
        return "_LicPer"
    else:
        return ""


        # Put the meta data in a dictionary from the csv
def set_metadata(job, project_id, keywords, tracker_version, v=1):


    # put all the values needed for manipulation in variables.
    textdate = job[5]
    decade = job[6]
    asset_number = job[0]
    source = job[1]
    source_id = job[4]
    copyright_holder = job[2]
    copyright_status = job[3]
    link = job[9]
    # pad asset number
    asset_number = retrosupport.process.pad_asset(asset_number, v)
    # parse date field

    dictdate = retrosupport.process.parse_date(textdate)
    # find our year categories
    if dictdate['year'] != "" or decade != "":
        year_categories_list = year_categories(dictdate['year'], decade)
    else:
        year_categories_list = ["Archival/No-Date"]
    # Check keywords
    if keywords == "$$Keywords":
        keywords = ""   # that is the default value and should be erased.

    # build filename
    file_name = project_id + "_" + asset_number
    if dictdate['year'] != "":
        file_name = file_name + "_" + dictdate['year']
        if dictdate['month'] != "":
            file_name = file_name + "_" + dictdate['month']
            if dictdate['day'] != "":
                file_name = file_name + "_" + dictdate['day']

    if "archive.org" in link.lower():
        file_name = file_name + "_IA"
        if copyright_holder != "":
            file_name = file_name + "_" + retrosupport.process.filename_format(copyright_holder)
    elif "tvnews.vanderbilt.edu" in link.lower():
        file_name =file_name + "_Vandy"
        if copyright_holder != "":
            file_name = file_name + "_" + retrosupport.process.filename_format(copyright_holder)
    else:
        field = retrosupport.process.filename_format(source)   # Source
        if field != "":
            file_name = file_name + "_" + field
    field = retrosupport.process.filename_format(source_id)   # Source ID
    if field != "":
        file_name = file_name + "_" + field

    # Attach copyright status
    copyright_label = copyright_labler(copyright_status)
    file_name = file_name + copyright_label

    # A place to hold the dictionary titles in case of google sheet column re-arrangement. Date column is always skipped
    # asset_number source copy_holder copyright_status source_id decade description details link master_status
    # alerts first_in first_out first_label second_in second_out second_label status_license
    # create our dictionary. A set for each version number of the tracker forms

    if tracker_version == "1.0":
        metadata = {'asset_number': asset_number, 'source': source, 'copy_holder': copyright_holder,
                    'copyright_status': copyright_status,
                    'source_id': source_id, 'decade': decade, 'description': job[7],
                    'details': retrosupport.process.clean_special_characters(job[8]), 'link': link,
                    'master_status': job[10], 'alerts': job[11], 'first_in': job[12],
                    'first_out': job[13], 'first_label': job[14], 'second_in': job[15],
                    'second_out': job[16], 'second_label': job[17],
                    # all items that don't come from the csv file
                    'location': "", 'project_id': project_id, 'formated_asset_number': asset_number,
                    'downloaded': False, 'screener': False, 'file_name': file_name, 'date': dictdate,
                    'file_name_ext': "", 'keywords': keywords, 'year_categories_list': year_categories_list,
                    'encoded': False, 'error': ""}
        return metadata
    elif tracker_version == "":
        print("Error: No tracker version present. Please check google sheet java script")
        exit()
    else:
        print("Error: Tracker version not compatible with this script")
        print("Also Cullen Golden missed his first day at Retro Report")
        exit()

    return "error"


# Download the video, return the results
def download_video(job, download_location, verbosity=1, ):
    if verbosity >= 1:
        print ("\nWorking on: " + job['project_id'] + "_" + job['formated_asset_number'])

    # Download file and store results
    result = retrosupport.retro_dl.retro_youtube_dl(job['link'], download_location, job['file_name'], verbosity)

    # Return results
    return result


# Create an excel spreadsheet
def excel(jobs, csv_path, errors, v=1):

    index = csv_path.rfind("/") + 1
    tstamp = time.strftime("%Y_%m_%d_T_%H_%M")  # create our time stamp
    file_location = csv_path[:index] + "Results_" + tstamp + ".xlsx"

    if v >= 3:
        print ('Creating excel sheet at: ' + file_location)

    # Create the workbook and sheet
    workbook = xlsxwriter.Workbook(file_location)
    workbook.set_size(1350, 2000)
    worksheet = workbook.add_worksheet('Retro Report')

    # Formatting
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'border': 6,
        'font_size': 20,
        'valign': 'vcenter'
    })

    link_header_format = workbook.add_format({
        'bold': True,
        'align': 'left',
        'border': 6,
        'font_size': 20,
        'valign': 'vcenter'
    })

    merge_format = workbook.add_format({
        'bold': True,
        'border': 6,
        'align': 'center',
        'fg_color': '#D7E4BC',
        'font_size': 44
    })

    file_name_success_format = workbook.add_format({
        'font_size': 12,
    })

    file_name_fail_format = workbook.add_format({
        'font_size': 14,
        'font_color': 'red',
    })

    download_success_format = workbook.add_format({
        'font_size': 16,
        'align': 'center',
        'fg_color': 'green',
        'border': 1
    })

    download_fail_format = workbook.add_format({
        'font_size': 16,
        'align': 'center',
        'fg_color': 'red',
        'bold': True,
        'border': 1
    })

    asset_success_format = workbook.add_format({
        'font_size': 12,
        'align': 'center',
    })

    link_format = workbook.add_format({
        'font_size': 12,
        'align': 'left',
    })

    asset_fail_format = workbook.add_format({
        'font_size': 14,
        'font_color': 'red',
        'align': 'center'
    })

    # Make all the headers
    worksheet.merge_range('A1:L1', 'Retro eMAM Auto Downloader Report', merge_format)
    worksheet.write('A2', 'Asset', header_format)
    worksheet.write('B2', '', header_format)
    worksheet.write('C2', 'File Name', header_format)
    worksheet.write('D2', '', header_format)
    worksheet.write('E2', 'Download', header_format)
    worksheet.write('F2', '', header_format)
    worksheet.write('G2', 'G.S.', header_format)
    worksheet.write('H2', '', header_format)
    worksheet.write('I2', 'Re', header_format)
    worksheet.write('J2', '', header_format)
    worksheet.write('K2', 'Error', header_format)
    worksheet.write('L2', '', header_format)
    worksheet.write('M2', '  Link', link_header_format)

    # Adjust column widths
    worksheet.set_column(0, 0, 9)
    worksheet.set_column(1, 1, 1)
    worksheet.set_column(2, 2, 90)
    worksheet.set_column(3, 3, 1)
    worksheet.set_column(4, 4, 18)
    worksheet.set_column(5, 5, 1)
    worksheet.set_column(6, 6, 8)
    worksheet.set_column(7, 7, 1)
    worksheet.set_column(8, 8, 8)
    worksheet.set_column(9, 9, 1)
    worksheet.set_column(10, 10, 10)
    worksheet.set_column(11, 11, 1)
    worksheet.set_column(12, 12, 200)

    # Adjust row widths
    worksheet.set_row(0, 70)
    worksheet.set_row(1, 35)

    # Freeze top two rows & other formatting
    worksheet.freeze_panes(2, 0)
    worksheet.set_tab_color('yellow')
    worksheet.set_default_row(24)

    # Fill out the sheet
    row = 2  # skip over title and column headers
    for job in jobs:
        if job['downloaded']:
            worksheet.write(row, 0, job['asset_number'], asset_success_format)
            worksheet.write(row, 2, job['file_name'], file_name_success_format)
            worksheet.write(row, 4, 'YES', download_success_format)
            worksheet.write(row, 6, job['screener'], file_name_success_format)
            if job['encoded'] is True:
                worksheet.write(row, 8, 'Yes', download_fail_format)
            else:
                worksheet.write(row, 8, 'No', download_success_format)
            if job['error'] != "":
                worksheet.write(row, 10, job['error'], download_fail_format)
        else:
            worksheet.write(row, 0, job['asset_number'], asset_fail_format)
            worksheet.write(row, 2, job['file_name_ext'], file_name_fail_format)
            worksheet.write(row, 4, 'NO!', download_fail_format)
            worksheet.write(row, 6, job['screener'], asset_success_format)
            worksheet.write(row, 8, 'No', download_success_format)
            if job['error'] != "":
                worksheet.write(row, 10, job['error'], download_fail_format)
            worksheet.write(row, 12, job['link'], link_format)

        row = row + 1
    row = row + 1
    #  Put in the errors
    if len(errors) > 0:
        ranged = "A" + str(row) + ":" + "K" + str(row)
        worksheet.merge_range(ranged, 'Errors', merge_format)
        row = row - 1
        worksheet.set_row(row, 60)
        row = row + 1
        for error in errors:
            worksheet.write(row, 10, '', download_fail_format)
            worksheet.write(row, 2, error, file_name_fail_format)
            row = row + 1

    workbook.close()


# check if we need to make a screener
# and if user specified a location
# return the location to make the screeners
def check_screeners(args, v=1):

    if args.google_screener:
        if args.screener_location is not None:
            if args.screener_location != "":  # custom location overrides default
                if v >= 1:
                    print ("you specified '-g' and '-x' flags")
                    print ("only one switch is necessary. Checking custom location")
                if os.path.isdir(args.screener_location):
                    if v >= 3:
                        print ("using custom screener location:")
                        print (args.screener_location)
                    return args.screener_location
                else:
                    if v >= 2:
                        print ("Custom Screener location is not a valid directory")
                        print ("Reverting to default 'Google Drive' location if available")
        locations = retrosupport.locate.google_drive(v)
        # check and see if we found the google drive
        if locations[0] == retrosupport.process.volume_result.not_found:
            if v >= 1:
                print ("No screener will be made Cannot find the Google Drive story path")
                print ("Check to see if Google Drive is mounted")
                return None
        else:
            # unpack google path list and return
            return locations[2]

    # No '-g' switch check for '-x'
    else:
        if args.screener_location is not None:
            if args.screener_location != "":  # custom location overrides default
                if os.path.isdir(args.screener_location):
                    if v >= 3:
                        print ("using custom screener location:")
                        print (args.screener_location)
                    # Path provided by user valid. return it
                    return args.screener_location
                else:
                    if v >= 2:
                        print ("Custom Screener location is not a valid directory")
                    return None


def google_drive_screener(job, path, v=1):

    # Grab the Project ID from file name
    project_id = retrosupport.process.parse_asset_label(job['file_name'])[0]
    # Find google drive archival expects the full path to the story folders
    # and Google Drive path in separate variables
    screener_path = retrosupport.locate.find_google_drive_archival(
        path[:21], path, project_id, v)

    if screener_path == retrosupport.process.volume_result.not_found:
        # we couldn't find the screener location in the Google Drive
        if v >= 1:
            print ("Could not find story folder in google drive for: " + job['file_name'])
            print ("No screener will be Made")
        job['screener'] = False
        return job
    else:
        # Find all files in our google drive location that have our asset number
        # No need to duplicate media on the Google Drive
        file_found_list = retrosupport.locate.find_asset(job['file_name'], screener_path)

        # Now check the results. Make screener if no file found
        if len(file_found_list) == 0:
            # add file name to path
            screener_path = screener_path + job['file_name']

            # create the screener
            if v >= 1:
                print ("\nScreener media source:")
                print (job['location'])
            retrosupport.media.create_screener(job['location'], screener_path, v)
            # Check and see if screener was really created
            if os.path.isfile(screener_path + ".mp4"):
                job['screener'] = True
                return job
        else:
            if v >= 1:
                print ("Looks like a screener already exists or there are duplicate asset #'s")
            job['screener'] = "Duplicate"

    return job


# What to do with the file after its downloaded
# Make screener, re-encode for compatibility, etc
def post_download(job, rough_screener_path, v=1):

    #  Check if we need to make a screener
    if rough_screener_path is not None:
        #  check if we need to run the old screener process
        #  Search for archival screener location etc.
        if rough_screener_path == "/Volumes/Google_Drive/_RETRO_SHARED/STORY_FOLDERS":
            job = google_drive_screener(job, rough_screener_path, v)
        else:
            # Custom download location
            if rough_screener_path[-1:] == '/':    # we don't need to add a trailing slash
                screener_path = rough_screener_path + job['file_name']
            else:                           # We do need to add a trailing slash
                screener_path = rough_screener_path + "/" + job['file_name']
                if v >= 1:
                    print ("Creating Screener at path:")            # create the screener file
                    print (screener_path)
            retrosupport.media.create_screener(job['location'], screener_path, v)
            # Check and see if screener was really created
            if os.path.isfile(screener_path + ".mp4"):
                job['screener'] = True
            else:
                job['screener'] = False

    # check to see if we need to rename a extension that is supposed to be mp4
    mp4_sites = ["gettyimages.com", "shutterstock.com"]

    for site in mp4_sites:
        if site in job['link'].lower():
            if "unknown_video" in job['file_name_ext']:
                new_location = string.replace(job['location'], "unknown_video", "mp4")  # replace with mp4 extension
                if not os.path.isfile(new_location):    # just in case for some reason file already exists
                    os.rename(job['location'], new_location)
                job['location'] = new_location
                job['file_name_ext'] = string.replace(job['file_name_ext'], "unknown_video", "mp4")

    # check to see if we need to re encode video
    encode_list = ["mkv", "webm", "wmv"]
    encode = False
    for extension in encode_list:
        if extension in job['file_name_ext']:
            encode = True

    if encode:
        #  we had a hit with our extension match
        #  strip old extension out of file.
        index = job['location'].rfind(".") + 1
        destination = job['location'][:index] + "mov"
        media_info = retrosupport.media.getinfo(job['location'])
        if v >= 3:
            print(media_info)
        #  no trimming supported. we take the whole file
        trim = [retrosupport.process.to_trim.false]

        new_location = retrosupport.media.ffmpeg(job['location'], destination, media_info,
                                                 retrosupport.process.resolution_type.same,
                                                 trim, v, retrosupport.process.formats.prores_lt)
        #  erase old fle put in path to new file
        if os.path.isfile(new_location):
            os.remove(job['location'])
            job['location'] = new_location
            job['encoded'] = True
            index = new_location.rfind("/") + 1
            job['file_name_ext'] = new_location[index:]

    return job


def find_xml(args):

    if args.xml_ingest == 2:
        return "xml_ingest2"
    else:
        return "xml_ingest3"


def random_generator():
    tstamp = time.strftime("%s")  # create our time stamp
    if len(tstamp) > 9:
        tstamp = tstamp[9]

    if tstamp == "0":
        return "The_Reckoning"
    elif tstamp == "1":
        return "The_Revenge"
    elif tstamp == "2":
        return "The_Catalyst"
    elif tstamp == "3":
        return "The_Reborn"
    elif tstamp == "4":
        return "The_Sequel"
    elif tstamp == "5":
        return "Cullen_Missed_His_First_Day_At_Work"
    elif tstamp == "6":
        return "This_Time_Its_Personal"
    elif tstamp == "7":
        return "The_Redemption"
    elif tstamp == "8":
        return "It_Goes_Up_To_Eleven"
    elif tstamp == "9":
        return "The_Return"
    else:
        return "Random_Word_Generator_Not_Working"

#  Determines weather or not the script should attempt to download the asset
def download_check(job, force_skip, v=1):
    answer = True  # Seed our answer
    message = ""

    # No source file. Can not process file
    if job['source'] == "":
        job['error'] = "No Source"
        answer = False
        message = "Asset has no source. Not adding to xml. Error reported.\nPlease check tracker or csv file"
        if v >= 1:
            print (message)
    # User elected to put all assets in future xml
    elif force_skip:
        answer = False    # user has selected to download the videos later
        message = "Force skip on. Adding to future download list"
    elif job['link'] == "":  # no link so return false
        if v >= 1:
            print ("Asset has no link. Adding to future download list")
        answer = False
        message = "Asset has no link. Adding to future download list"
    else:
        web_url = ["archive.org", "vanderbilt.edu"]
        for url in web_url:
            if url in job['link']:
                answer = False
                message = "Non script supported website. Adding to future downloads list"
                if v >= 1:
                    print (message)

    pack = [answer, job, message]
    return pack


def choose_extension(job, ext):

    if "archive.org" in job['link']:
        return ".mp4"
    elif "aparchive.com" in ['link']:
        return ".mp4"
    elif "gettyimages.com" in ['link']:
        return ".mp4"
    elif "archives.gov" in ['link']:
        return ".mp4"
    elif "vanderbilt.edu" in ['link'] or "vanderbilt" in job['source'].lower():
        return ".mpg"
    else:
        if ext[0] == ".":
            return ext
        else:
            ext = "." + ext
            return ext


def main():

    print("")  # a nice blank space after the user puts in all the input
    # get arguments set up
    unpack = set_argparse()  # returns list of parsed arguments and the parser itself

    #    parser = unpack[0]  # unpack the parser
    args = unpack[1]  # unpack the parsed args

    check_args(args)
    verbosity = args.verbosity
    csv_path = args.input
    force_skip = args.later
    xml_path = find_xml(args)

    # check about the extension
    extension = ".mov"
    if args.extension is not None:
        # check for the '.'
        if args.extension[0] == ".":
            extension = args.extension
        else:
            extension = "." + args.extension
    force_extension = args.force_extension

    # setup log file. Will only be created if verbosity is set to 3 or greater
    if verbosity >= 3:
        tstamp = time.strftime("%Y_%m_%d_T_%H_%M")  # hold thr current date and time
        index = csv_path.rfind("/") + 1
        log_path = csv_path[:index] + "emam_log_" + tstamp + "_.txt"
        print("Verbosity set to 3 or greater. Generating log file at: " + log_path)
        f = open(log_path, str('w+'))
        f.write(str("log opened " + tstamp))
        f.write(str("\n\nUser Input:\n"))
        f.write(str(args))
        f.write(str("\nEnd user input\n\n"))
        f.write(str("Checking automated required arguments:\n"))

    # Multi threading not supported yet. Warn user if enabled
    if args.multi_thread:
        if verbosity >= 1:
            print ("You enabled Multi threading. At this point it is not supported but hopefully soon")
            print ("The -m flag will be ignored\n")

    # put all our jobs from the csv file into an array
    csv_dump = csv_process(csv_path, verbosity)  # ingest the csv file
    csv_first_pass = []  # create our list to put jobs in

    tracker_version = csv_dump[0][0]    # the all important tracker version so the right columns get
    # the correct meta data assignment

    # check the project ID
    if args.project_id is None:
        project_id = csv_dump[0][1]  # extract the project ID number
        if verbosity >= 2:
            print ("Using google sheet provided project id: " + project_id)
            if verbosity >= 3:
                f.write(str("Using Google Sheet provided Project ID: "))
                f.write(str(project_id))
                f.write(str("\n"))
    else:
        project_id = args.project_id
        if verbosity >= 2:
            print ("Using user provided provided project id: " + project_id)
            if verbosity >= 3:
                f.write(str("Using User provided project ID: "))
                f.write(str(project_id))
                f.write(str("\n"))

    if project_id == "$$ProjectID":
        if verbosity >= 1:
            print ("The Google Sheet JavaScript did not provide a project ID")
            print ("Specify your own project ID with the -r flag. Downloader will not continue")
            if verbosity >= 3:
                f.write(str("Google Sheet failed to provide project ID. Program will Exit"))
                f.close()
        exit()

    # Grab the eMAM category for assets
    categories = []
    if args.category is not None:
        if args.category != "":
            categories.append(args.category)

    if csv_dump[0][2] != "" and csv_dump[0][3] != "":
        categories.append(csv_dump[0][3] + "/" + project_id + " " + csv_dump[0][2] + "/" + csv_dump[0][4])
        if verbosity >= 2:
            message = ""
            for category in categories:
                message = message + " " + category
            message = "Category path(s): " + categories
            print (message)
            if verbosity >= 3:
                f.write(str("Google sheet provided "))
                f.write(str(message))
                f.write(str("\n"))
    else:
        if verbosity >= 1:
            print ("No category defined\n Will not go on")
            print ("You must define a category")
            if verbosity >= 3:
                f.write(str("Google Sheet failed to provide the category path\n"))
                f.write(str("program will exit"))
                f.close()
        exit()

    # Take care of keywords
    key_words = ""
    if csv_dump[0][5] != "" and csv_dump[0][5] != "$$Keywords":
        key_words = csv_dump[0][5]

        if verbosity >= 2:
            print ("Keywords are: " + key_words)

        if verbosity >= 3:
            f.write(str("Google sheet provided Keywords: "))
            f.write(key_words)
            f.write(str("\n"))
    else:
        if verbosity >= 2:
            message = "No Keywords provided by Google Sheet"
            print (message)
            if verbosity >= 3:
                f.write(str(message))
                f.write(str("\n"))

    if verbosity >= 3:
        f.write(str("End check of automated arguments\n\n"))

    # copy the rest of the list, everything except first element
    after_first_item = False
    for item in csv_dump:
        if after_first_item:    # so the first line in this list is skipped
            csv_first_pass.append(item)
        after_first_item = True  # need to mark we passed the first item

    if verbosity >= 1:
        message = str(len(csv_first_pass)) + " jobs to process"
        print (message)

    jobs = []  # create job list
    processed_jobs = []   # create list to hold processed jobs
    errors = []  # hold the jobs with errors
    links = 0  # hold the number of jobs with links

    # Variable to determine if me make screener or not
    # Value is none if not. Path for screener location if yes
    screeners = check_screeners(args, verbosity)

    # Loop through the list and format each job
    if verbosity >= 3:
        f.write(str("Begin looping through job list:\nNote date won't display correct in log\n\n"))

    csv_count = 2   # keep track of what line we are on for error reporting. Start at two because 1st line skipped
    for item in csv_first_pass:

        #  Catch Errors. Important so we don't put bad data into emam
        if len(item) < 19:  # error catch not enough elements
            # all jobs should hav at least 19 elements
            if str(item[0]) != "":
                message_assest = str(item[0])
            else:
                message_assest = "Unknown at csv line: " + str(csv_count) + " "
            message = "Asset: " + message_assest + " has too few elements: " + str(len(item))
            errors.append(message)
            if verbosity >= 2:
                print ("Job has too few items:\n" + str(item))
            if verbosity >= 3:
                f.write(str("Asset has too few elements. Skipping: "))
                f.write(str(item))
                f.write(str("\n"))
        elif not item[0].isdigit():  # No asset number
            #  log
            if verbosity >= 3:
                f.write(str("Asset is missing its asset #. Skipping: "))
                f.write(str(item))
                f.write(str("\n"))
            message = "Line in CSV File Missing asset number at csv line: " + str(csv_count)
            errors.append(message)
        else:
            # put all our meta data in a nice dictionary
            metadata = set_metadata(item, project_id, key_words, tracker_version, verbosity)
            jobs.append(metadata)

            # log
            if verbosity >= 3:
                message = "Asset #: " + item[0] + "\n"
                f.write(str(message))
                for k, v in metadata.items():
                    f.write(str("\t"))
                    if hasattr(v, '__iter__'):
                        f.write(str(k))
                    else:
                        line = k + " : " + str(v) + '\n'
                        f.write(str(line))
                f.write(str("\n"))

            if item[5] != "":  # Count the number of lines with links
                links = links + 1
        csv_count = csv_count + 1

    if verbosity >= 2:  # Some feedback for our user
        message = str(len(jobs)) + " entries submitted, " + str(links) + " with links to download:"
        print (message)

        #  log
        if verbosity >= 3:
            f.write(str(message))
            f.write(str("\n"))

        for job in jobs:
            if job['link'] != "":
                print ("\tFile name for asset " + job['asset_number'] + " is: " + job['file_name'])

    # put save location in variable. append trailing '/' if it does not exist.
    if args.output_directory[:0] == "/":
        location = args.output_directory
    else:
        location = args.output_directory + "/"

    message = "Begin loop through jobs. Checking download status and attempting downloads\n"
    if verbosity >= 1:
        print (message)
        if verbosity >= 3:
            f.write(str(message))
    # download the videos in a loop
    for job in jobs:
        # clean up timecode in and outs
        job = subclip(job, verbosity)
        unpack = download_check(job, force_skip, verbosity)  # boolean that will tell us to download or not and job
        try_download = unpack[0]
        job = unpack[1]
        test_message = unpack[2] + "\n"

        # log
        if verbosity >= 3:
            message = "\nAsset: " + job['asset_number'] + "\n\t"
            f.write(str(message))
            f.write(str(test_message))
            if try_download:
                f.write(str("Passed Download Test"))
            else:
                f.write(str("Failed Download Test"))

        if job['error'] != "":  # error occured where we cannot put asset in xml for processing
            message = "Asset: " + job['asset_number'] + " " + job['error']
            errors.append(message)
        else:  # its going into an xml lets see which one
            if try_download:  # check to see if a link exists
                download = download_video(job, location, verbosity)  # download the video store result

                #  log
                if verbosity >= 3:
                    message = "download result from download_video function: " + str(download)
                    f.write(str(message))

                if download == 0:  # download failed
                    job['downloaded'] = False
                    processed_jobs.append(job)
                else:  # Double Check make sure file is there

                    try:
                        if os.path.isfile(str(download)):    # Success? two more tests
                            # check for funky file extensions
                            path, file_name = os.path.split(str(download))
                            index = file_name.rfind(".") + 1
                            extension = file_name[index:]
                            bad_extensions = ['html']
                            if extension in bad_extensions:
                                message = "\nAppears the file downloaded was bogus. html"
                                if verbosity >= 1:
                                    print (message)
                                    if verbosity >= 3:
                                        f.write(str(message))
                                job['downloaded'] = False
                                job['error'] = "html file"
                                processed_jobs.append(job)
                                # remove bogus file
                                os.remove(str(download))
                                # check for file too small
                            elif os.path.getsize(str(download)) < 2000000:
                                message = "\nThe file downloaded is too small"
                                if verbosity >= 1:
                                    print (message)
                                    if verbosity >= 3:
                                        size = os.path.getsize(str(download)) / 1000000
                                        message = message + "\nFile size = " + str(size) + "MB\n"
                                        f.write(str(message))
                                job['downloaded'] = False
                                job['error'] = "Size"
                                processed_jobs.append(job)
                                # remove bogus file
                                os.remove(str(download))
                            else:
                                job['location'] = download  # path to the file returned from download_video
                                # get the real file name with the extension and save it
                                job['downloaded'] = True
                                job['file_name_ext'] = file_name
                                job = post_download(job, screeners, verbosity)
                                processed_jobs.append(job)
                        else:
                            job['downloaded'] = False   # files doesn't exists so no download
                            processed_jobs.append(job)
                    except TypeError:
                        job['downloaded'] = False  # files doesn't exists so no download
                        job['error'] = "ck file"
                        processed_jobs.append(job)
                        #  log
                        message = "Strange result from youtube dl. Maybe partial file download for asset: " \
                                  + job['asset_number']
                        f.write(str(message))
                        if verbosity >= 1:
                            message = job['file_name'] + " Will be added to future import xml"
                            print(str(message))
                            #  log
                            if verbosity >= 3:
                                f.write(str(message))
            else:
                job['downloaded'] = False  # No link so mark as failed download
                processed_jobs.append(job)
                if verbosity >= 1:
                    message = job['file_name'] + " Will be added to future import xml"
                    print(str(message))
                    #  log
                    if verbosity >= 3:
                        f.write(str(message))

    # Split the list in two. One for downloaded assets and one for all others
    downloaded_jobs = []    # holds the assets that we have ready
    future_import_jobs = []  # holds the assets for a separate xml file that will be used for batch import in the future

    for job in processed_jobs:
        if job['downloaded']:   # downloaded holds a boolean
            downloaded_jobs.append(job)  # this job was downloaded
        else:   # These jobs were not downloaded, add to separate list
            future_import_jobs.append(job)

    # Check and see if we have any downloaded jobs
    if len(downloaded_jobs) > 0:

        # create a log file of the data before its sent to xml
        if verbosity >= 3:
            for items in downloaded_jobs:
                for k, v in items.items():
                    if hasattr(v, '__iter__'):
                        f.write(k)
                    else:
                        line = k + " : " + str(v) + '\n'
                        f.write(line)
                f.write(str("\n"))

        # Get the xml ready for files that we have now
        downloaded_job_xml_list = retrosupport.process.emam_metadata_format(downloaded_jobs, categories,
                                                                retrosupport.process.SideCarType.tracker, xml_path)

        # Create our xml file
        tstamp = time.strftime("%Y_%m_%d_T_%H_%M")      # hold thr current date and time
        if os.path.isfile(location + 'sidecar_' + tstamp + '.xml'):
            random_word = random_generator()
            location = location + 'sidecar_part2_' + random_word + '_' + tstamp + '.xml'
        else:
            location = location + "sidecar_" + tstamp + ".xml"

        retrosupport.emamsidecar.generate_sidecar_xml('DlmCO%2frHfqn8MFWM72c2oEXEdfnMecNFm8Mz413k%2fUzRtOsyTzHvBg%3d%3d'
                                                      , downloaded_job_xml_list, location)

    # Get xml ready for files we will have in the future

    if len(future_import_jobs) > 0:     # make sure we have items in the list

        # need to add a generic file extension since files weren't downloaded
        if force_extension:
            for job in future_import_jobs:
                job['file_name_ext'] = job['file_name'] + extension   # Mov's are most likely extension
        else:
            for job in future_import_jobs:
                job['file_name_ext'] = job['file_name'] + choose_extension(job, extension)

        # format our metadata
        future_job_xml_list = retrosupport.process.emam_metadata_format(future_import_jobs, categories, retrosupport.
                                                                        process.SideCarType.tracker, xml_path)

        # get the location to save to, coming from input file
        index = csv_path.rfind("/") + 1
        tstamp = time.strftime("%Y_%m_%d_T_%H_%M")    # create our time stamp
        # Check and see if cullen is running two of these jobs again
        if os.path.isfile(csv_path[:index] + "future_sidecar_" + tstamp + ".xml"):
            random_word = random_generator()
            location = csv_path[:index] + "future_sidecar_part2_" + random_word + '_' + tstamp + ".xml"
        else:
            location = csv_path[:index] + "future_sidecar_" + tstamp + ".xml"
        retrosupport.emamsidecar.generate_sidecar_xml('DlmCO%2frHfqn8MFWM72c2oEXEdfnMecNFm8Mz413k%2fUzRtOsyTzHvBg%3d%3d'
                                                      , future_job_xml_list, location)
    # Make spreadsheet report
    excel(processed_jobs, csv_path, errors, verbosity)
    if verbosity >= 3:
        tstamp = time.strftime("%Y_%m_%d_T_%H_%M")  # hold thr current date and time
        message = "Closing log " + tstamp
        f.write(str(message))
        f.close()
    exit()

if __name__ == "__main__":
    main()
