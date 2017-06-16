#!/usr/bin/env python
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
from retrosupport import process
from retrosupport import media
from retrosupport.process import volume_result
from retrosupport.retro_dl import retro_youtube_dl
from retrosupport.emamsidecar import Asset, FileAction, IngestAction, CustomMetadata, Marker, generate_sidecar_xml, Subclip


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

    parser.add_argument("-g", "--google_screener", action="store_true", help="Create mp4's for the google drive")

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

    if csv_file == volume_result.not_found:
        print ("No file found at: " + path)
        print ("Please find your csv file and try again")
        exit()
    else:
        reader = csv.reader(csv_file)
        jobs_list = list(reader)  # convert reader to list
        if verbosity >= 3:
            print ("output of CSV file:")
            for line in jobs_list:
                print (line)
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
        print ("Please specifiy a valid directory to save to with the -d swtich")
        exit()  # Cuz we have nowhere to put anything
    elif not os.path.isdir(args.output_directory):
        print ("The directory you specified to save to does not exist: "
               + args.output_directory + " please specifiy a valid directory to save to")
        exit()  # Cuz we have nowhere to put anything


# Turn the spelled month into the number
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
    else:  # text not standard month. Make it unknown
        string = "11"

    return string


# parse the expected date format from google sheets YYYY MMM DD
def parse_date(string, v=1):

    # split the string into a list separated by spaces
    elements = string.split()

    # touble shooting
    if v >= 3:
        print ("\nraw string sent to parse_date:\n " + string)
        print ("String broken into elements:")
        print (elements)

    months = ["dec", "december", "nov", "november", "oct", "october", "sep", "september",
              "aug", "august", "jul", "july", "jun", "june", "may", "apr", "april",
              "mar", "march", "feb", "february", "jan", "january"]

    dictdate = {'year': "", 'month': "", 'day': ""}  # create date dictionary. seed with our "unknown date"

    # go through possible date formats
    if len(elements) == 3:  # what we should get
        dictdate['year'] = elements[0]
        dictdate['month'] = month_text_to_number(elements[1])
        dictdate['day'] = elements[2]
    elif len(elements) == 1:  # just a year maybe?
        if len(elements[0]) == 4:
            dictdate['year'] = elements[0]
    elif len(elements) == 2:  # month and year?
        for item in elements:
            if len(item) == 4:
                dictdate['year'] = item
            # check for months
            elif item in months:
                dictdate['month'] = month_text_to_number(item)

            elif item.isdigit():
                if int(item) <= 12:  # can't b more than 12. value will be ignored if so
                    if len(item) == 1:
                        item = "0" + item  # month is only 1 digit pad with string
                    dictdate['month'] = item

    if v >= 3:
        print ("Post dictdate process")
        print (dictdate)

    return dictdate


# replace spaces with '_' and '/' with '-' and take out quotes
def format_string(string):
    return_string = string.replace(" ", "_")
    return_string = return_string.replace("/", "-")
    return_string = return_string.replace('"', "")
    return_string = return_string.replace("'", "")
    return_string = return_string.replace(';', "")
    return_string = return_string.replace(",", "")

    return return_string


# create our standard asset label from the number
def pad_asset(asset, v=1):
    if len(asset) == 1:
        return_asset = "A00" + asset
        if v >= 3:
            print ("\nOriginal Asset Variable: " + asset)
            print ("Modified Asset Variable: " + return_asset)
    elif len(asset) == 2:
        return_asset = "A0" + asset
        if v >= 3:
            print ("\nOriginal Asset Variable: " + asset)
            print ("Modified Asset Variable: " + return_asset)
    elif len(asset) == 3:
        return_asset = "A" + asset
        if v >= 3:
            print ("\nOriginal Asset Variable: " + asset)
            print ("Modified Asset Variable: " + return_asset)
    else:
        return_asset = "A"

    return return_asset


# Put the meta data in a dictionary from the csv
def create_metadata(job, project_id, v=1):

    # pad asset number
    asset_number = pad_asset(job[0], v)
    # parse date field
    textdate = job[3]
    dictdate = parse_date(textdate)

    # build filename
    file_name = project_id + "_" + asset_number
    if dictdate['year'] != "":
        file_name = file_name + "_" + dictdate['year']
    if dictdate['month'] != "":
        file_name = file_name + "_" + dictdate['month']
    if dictdate['day'] != "":
        file_name = file_name + "_" + dictdate['day']
    field = format_string(job[1])
    if field != "":
        file_name = file_name + "_" + field
    field = format_string(job[2])
    if field != "":
        file_name = file_name + "_" + field

    # create our dictionary
    metadata = {'file_name': file_name, 'date': dictdate, 'source': job[1], 'source_id': job[2], 'description': job[4],
                'link': job[5], 'in': job[6], 'out': job[7], 'notes': job[8], 'copy_holder': job[9], 'location': "",
                'license_status': job[10], 'copyright_status': job[11], 'project_id': project_id,
                'asset_number': job[0], 'formated_asset_number': asset_number, 'downloaded': False, 'screener': False,
                'file_name_ext': ""}

    return metadata


# Download the video, return the results
def download_video(job, download_location, verbosity=1, ):
    if verbosity >= 1:
        print ("\nWorking on: " + job['project_id'] + "_" + job['formated_asset_number'])

    # Download file and store results
    result = retro_youtube_dl(job['link'], download_location, job['file_name'], verbosity)

    # Return results
    return result


# Create an excel spreadsheet
def excel(jobs, download_location, v=1):

    file_location = download_location + 'Results.xlsx'
    if v >= 3:
        print ('Creating excel sheet at: ' + file_location)

    # Create the workbook and sheet
    workbook = xlsxwriter.Workbook(file_location)
    workbook.set_size(1275, 1800)
    worksheet = workbook.add_worksheet('Retro Report')

    # Formatting
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
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

    asset_fail_format = workbook.add_format({
        'font_size': 14,
        'font_color': 'red',
        'align': 'center'
    })

    # Make all the headers
    worksheet.merge_range('A1:G1', 'Retro eMAM Auto Downloader Report', merge_format)
    worksheet.write('A2', 'Asset', header_format)
    worksheet.write('B2', '', header_format)
    worksheet.write('C2', 'File Name', header_format)
    worksheet.write('D2', '', header_format)
    worksheet.write('E2', 'Downloaded', header_format)
    worksheet.write('F2', '', header_format)
    worksheet.write('G2', 'Screener', header_format)

    # Adjust column widths
    worksheet.set_column(0, 0, 9)
    worksheet.set_column(1, 1, 1)
    worksheet.set_column(2, 2, 100)
    worksheet.set_column(3, 3, 1)
    worksheet.set_column(4, 4, 20)
    worksheet.set_column(5, 5, 1)
    worksheet.set_column(6, 6, 18)

    # Adjust row widths
    worksheet.set_row(0, 70)
    worksheet.set_row(1, 35)
    # worksheet.set_r

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
        else:
            worksheet.write(row, 0, job['asset_number'], asset_fail_format)
            worksheet.write(row, 2, job['file_name'], file_name_fail_format)
            worksheet.write(row, 4, 'NO!', download_fail_format)
            worksheet.write(row, 6, job['screener'], file_name_success_format)
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
        if locations[0] == volume_result.not_found:
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

    if screener_path == volume_result.not_found:
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
def post_download(args, job, rough_screener_path, v=1):

    #  Check if we need to make a screener
    if rough_screener_path is not None:
        #  check if we need to run the old screener process
        #  Search for archival screener location etc.
        if rough_screener_path == "/Volumes/Google_Drive/_RETRO_SHARED/STORY_FOLDERS":
            job = google_drive_screener(job, rough_screener_path, v)
            return job
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
                return job
            else:
                job['screener'] = False

    return job


def emam_metadata_format(jobs, category):

    list_assets = []
    for job in jobs:
        # Asset information
        asset = Asset()
        asset.title = job['file_name']
        asset.description = job['description']
        asset.file_name = job['file_name_ext']
        asset.file_path = "\\\\10.0.2.8\\xml_ingest"
        asset.file_action = FileAction.MOVE
        asset.ingest_action = IngestAction.CREATE_NEW_ASSET

        # Define custom metadata fields.
        custom_metadata = []
        # Mandatory fields
        metadata = CustomMetadata()  # Set metadata as CustomMetadata object
        metadata.standard_id = 'CUST_FLD_ASSET LABEL_13'    # Add the id for metadata field
        metadata.value = job['file_name']       # Add the value of the feild
        custom_metadata.append(metadata)    # append metadata to the list
        metadata = CustomMetadata()     # reset custom metadata object
        metadata.standard_id = 'CUST_FLD_ASSET NUMBER_25'
        metadata.value = job['asset_number']
        custom_metadata.append(metadata)
        metadata = CustomMetadata()
        metadata.standard_id = 'CUST_FLD_SOURCE_17'
        metadata.value = job['source']
        custom_metadata.append(metadata)
        metadata = CustomMetadata()
        metadata.standard_id = 'CUST_FLD_PROJECT ID_29'
        metadata.value = job['project_id']
        custom_metadata.append(metadata)

        # Non mandatory fields
        if job['source_id'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_SOURCE ID_18'
            metadata.value = job['source_id']
            custom_metadata.append(metadata)
        if job['description'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_DESCRIPTION_19'
            metadata.value = job['description']
            custom_metadata.append(metadata)
        if job['link'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_LINK_20'
            metadata.value = job['link']
            custom_metadata.append(metadata)
        if job['notes'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_NOTES_32'
            metadata.value = job['notes']
            custom_metadata.append(metadata)
        #  Extract date
        dict_date = job['date']
        if dict_date['year'] != "":  # use the year as the condition if a date is present
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_DATE_5'
            date = dict_date['year']
            if dict_date['month'] != "":    # test if month is present
                date = date + "/" + dict_date['month']
            if dict_date['day'] != "":
                date = date + "/" + dict_date['month']
            print date
            metadata.value = date
            custom_metadata.append(metadata)

        # load meta data into asset
        asset.custom_metadata = custom_metadata

        # Add category
        asset.categories = category

        # load asset into list
        list_assets.append(asset)

    return list_assets


def main():

    print ("")  # a nice blank space after the user puts in all the input
    # get arguments set up
    unpack = set_argparse()  # returns list of parsed arguments and the parser itself

    #    parser = unpack[0]  # unpack the parser
    args = unpack[1]  # unpack the parsed args

    check_args(args)
    verbosity = args.verbosity
    csv_path = args.input

    # Multithreading not supported yet. Warn user if enabled
    if args.multi_thread:
        print ("You enabled Multithreading. At this point it is not supported but hopefully soon")
        print ("The -m flag will be ignored\n")

    # put all our jobs from the csv file into an array
    csv_dump = csv_process(csv_path, verbosity)  # ingest the csv file
    csv_first_pass = []  # create our list to put jobs in

    # check the project ID
    if args.project_id is None:
        project_id = csv_dump[0][0]  # extract the project ID number
        if verbosity >= 2:
            print ("Using google sheet provided project id: " + project_id)
    else:
        project_id = args.project_id
        if verbosity >= 2:
            print ("Using user provided provided project id: " + project_id)

    if project_id == "$$ProjectID":
        print ("The Google Sheet JavaScript did not provide a project ID")
        print ("Specify your own project ID with the -r flag. Downloader will not continue")
        exit()

    # Grab the eMAM category for assets

    if csv_dump[0][1] != "" and csv_dump[0][2] != "":
        category = []
        category.append(csv_dump[0][2] + "/" + project_id + " " +
                        csv_dump[0][1] + "/" + csv_dump[0][3])  # the category from the csv file
    else:
        print ("No category defined\n Will not go on")
        print ("You must define a category")
        exit()

    if verbosity >= 2:
        print ("Category path is: " + category)

    # copy the rest of the list, everything except first element
    after_first_item = False
    for item in csv_dump:
        if after_first_item:
            csv_first_pass.append(item)
        after_first_item = True  # need to mark we passed the first item

    if verbosity >= 1:
        print (str(len(csv_first_pass)) + " jobs to process")

    jobs = []  # create job list
    processed_jobs = []   # create list to hold processed jobs
    links = 0  # hold the number of jobs with links

    # Variable to determine if me make screener or not
    # Value is none if not. Path for screener location if yes
    screeners = check_screeners(args, verbosity)

    # Loop through the list and format each job
    for item in csv_first_pass:

        # put all our meta data in a nice dictionary
        metadata = create_metadata(item, project_id, verbosity)
        jobs.append(metadata)
        if item[5] != "":  # Count the number of lines with links
            links = links + 1

    if verbosity >= 2:  # Some feedback for our user
        print ("\n" + str(len(jobs)) + " entries submitted, " + str(links) + " with links to download:")
        for job in jobs:
            if job['link'] != "":
                print ("\tFile name for asset " + job['asset_number'] + " is: " + job['file_name'])

    # put save location in variable. append trailing '/' if it does not exist.
    if args.output_directory[:0] == "/":
        location = args.output_directory
    else:
        location = args.output_directory + "/"

    # download the videos in a loop
    for job in jobs:
        if job['link'] != "":  # check to see if a link exists
            download = download_video(job, location, verbosity)  # download the video store result
            if verbosity >= 3:
                print ("\ndownload result from download_video function:")
                print (download)

            if download == 0:  # download failed
                job['downloaded'] = False
                processed_jobs.append(job)
            else:  # Double Check make sure file is there
                if os.path.isfile(download):    # Success! store the results
                    job['downloaded'] = True
                    job['location'] = download  # download is the path to the file returned from download_video
                    # get the real file name with the extension and save it
                    head, tail = os.path.split(download)
                    job['file_name_ext'] = tail
                    job = post_download(args, job, screeners, verbosity)
                    processed_jobs.append(job)
                else:
                    job['downloaded'] = False   # files doesn't exists so no download
                    processed_jobs.append(job)
        else:
            job['downloaded'] = False  # No link so mark as failed download
            processed_jobs.append(job)
            print ("\nSkipping " + job['file_name'] + "has no link")

    excel(processed_jobs, location, verbosity)

    # Split the list in two. One for downloaded assets and one for all others
    downloaded_jobs = []    # holds the assets that we have ready
    future_import_jobs = []  # holds the assets for a separate xml file that will be used for batch import in the future

    for job in processed_jobs:
        if job['downloaded']:   # downloaded holds a boolean
            downloaded_jobs.append(job)  # this job was downloaded
        else:   # These jobs were not downloaded, add to separate list
            # Don't add to list if they are vanderbilt assets
            if job['source'].lower() == "vanderbilt":
                print ("vandy. not adding")
            elif job['source'].lower() == "vandy":
                print ("vandy. not adding")
            else:
                future_import_jobs.append(job)

    # Check and see if we have any downloaded jobs
    if len(downloaded_jobs) > 0:

        # Get the xml ready for files that we have now
        downloaded_job_xml_list = emam_metadata_format(downloaded_jobs, category)

        # Create our xml file
        tstamp = time.strftime("%Y_%m_%d_T_%H_%M")      # hold hte current date and time
        location = location + "sidecar_" + tstamp + ".xml"

        generate_sidecar_xml('DlmCO%2frHfqn8MFWM72c2oEXEdfnMecNFm8Mz413k%2fUzRtOsyTzHvBg%3d%3d', downloaded_job_xml_list,
                             location)

    # Get xml ready for files we will have in the future
    if len(future_import_jobs) > 0:     # make sure we have items in the list
        # need to add a generic file extension since files weren't downloaded
        for job in future_import_jobs:
            job['file_name'] = job['file_name'] + ".mov"   # Mov's are most likely extension

        future_job_xml_list = emam_metadata_format(future_import_jobs, category)  # format our metadata

        # get the location to save to, coming from input file
        index = csv_path.rfind("/") + 1
        tstamp = time.strftime("%Y_%m_%d_T_%H_%M")    # create our time stamp
        location = csv_path[:index] + "future_sidecar_" + tstamp + ".xml"
        generate_sidecar_xml('DlmCO%2frHfqn8MFWM72c2oEXEdfnMecNFm8Mz413k%2fUzRtOsyTzHvBg%3d%3d',
                             future_job_xml_list,
                             location)

if __name__ == "__main__":
    main()
