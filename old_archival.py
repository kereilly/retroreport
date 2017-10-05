#  Create xml for sidecar ingest of old archival materail

import csv
import argparse
import os.path
import re
import xlsxwriter
import retrosupport
import sys
from retrosupport import process
from collections import defaultdict

# for unicode type issues when reading the csv file
reload(sys)
sys.setdefaultencoding('utf8')

def set_argparse():
    # Start things off using pythons argparse. get user input and give help information
    parser = argparse.ArgumentParser(
        description="Old project meta data matcher program thingy Version .1",
        epilog="Don't Panic"
    )

    # arguments for user to put in

    parser.add_argument("-i", "--input", type=str,
                             help="Specify a CSV file for matching metadata")
    parser.add_argument("-d", "--directory", type=str,
                        help="Specify a directory to match metadata with")

    parser.add_argument("-r", "--project_id", type=str,
                             help="Project ID of archival you are importing")

    parser.add_argument("-c", "--category", type=str,
                        help="Category Path for archival you are importing")

    parser.add_argument("-v", "--verbosity", type=int, default=1, choices=[0, 1, 2, 3],
                        help="Increase, 2, or decrease, 0, the level of output. 3 is debug mode. Default is 1")

    parser.add_argument("-p", "--premiere", action="store_true", help="Convert media automatically if it is "
                                                                      "not premiere compatible")

    parser.add_argument("-o", "--xml_ingest", type=int, choices=[1, 2, 3, 4, 5], help="Raid location usage")


    # have argparse do its thing
    args = parser.parse_args()

    # pack up what we need to bring back to main
    pack = (parser, args)
    return pack

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
    if args.directory is None:
        print ("You didn't specify a directory to save to")
        print ("Please specify a valid directory to save to with the -d switch")
        exit()  # Cuz we have nowhere to put anything
    elif not os.path.isdir(args.directory):
        print ("The directory you specified to save to does not exist: "
               + args.directory + " please specify a valid directory to save to")
        exit()  # Cuz we have nowhere to put anything

    # check project ID
        if args.project_id is None:
            print ("You must enter a Project ID with -r. For example:")
            print ("-r RR308 or:")
            print ("-r Cullen missed his first day at work.")
            exit()  # Seriously we aren't going to continue with out this

    # Check category
        if args.category is None:
            print ("Specify category path with -c option")
            print ("Example: RR Stories/RR258 Vaccine/Archival")
            print ("Please make sure it matches your category path in eMAM")


# Create dictionary with all the metadata we can handle
def set_metadata(local_file, path, v=1):
    # Create dictionary for our files
    dict_temp = {'file_name': local_file, 'file_path': path, 'asset_number': "", 'source': "", 'source_id': "",
                 'description': "", 'link': "", 'dict_date': {'year': "", 'month': "", 'day': "", 'decade': ""}}
    return dict_temp


def get_unique_asset_numbers(media_list, v=1):

    new_list = []
    for item in media_list:
        new_list.append(item['asset_number'])
    asset_set = set(new_list)
    new_list = list(asset_set)
    return new_list


def sort_list(list_to_sort, v=1):

    list_duplicates = []
    list_non_dup_archival_media = []

    asset_numbers = get_unique_asset_numbers(list_to_sort)
    for asset in asset_numbers:
        list_temp = []
        for item in list_to_sort:
            if item['asset_number'] == int(asset):
                list_temp.append(item)
        if len(list_temp) > 1:  # We have duplicates. save this list
            list_duplicates.append(list_temp)
        elif len(list_temp) == 1:  # no duplicates. Don't save the list save the one item
            list_non_dup_archival_media.append(list_temp[0])

        package = [list_duplicates, list_non_dup_archival_media]
    return package


# simple functions to get a key to sort lists.
def get_key_file_size(item):
    return item['file_size']


def get_key_file_value(item):
    return item['file_value']


def get_key_asset_number(item):
    return item['asset_number']


def choose_file(asset_list, v=1):

    # easy ones first. take masters and trimmed files. Ones that are both take precedent
    # Media w/ both conditions need to be searched for sepretly. In case the single condition file is higher in the list
    for media_file in asset_list:
        if "master" in media_file['file_name'].lower() and "trimmed" in media_file['file_name'].lower():
            return media_file
        if "master" in media_file['file_name'].lower() and "redux" in media_file['file_name'].lower():
            return media_file
    for media_file in asset_list:
        if "master" in media_file['file_name'].lower():
            return media_file
        elif "trimmed" in media_file['file_name'].lower():
            return media_file
        else:  # no hits, we need to record some information, make the dict keys to hold info
            media_file.update({'file_size': 1, 'file_extension': "", 'file_value': 0})

    # now it gets more complicated. Favor files smaller in size unless they have undesirable extensions.

    # Add value for bad extensions, get file size
    undesirable_formats = [".webm", "mkv"]
    for media_file in asset_list:
        for extension in undesirable_formats:
            if extension in media_file['file_name']:
                media_file['file_value'] = media_file['file_value'] + 3  # add three points because of incapability
        media_file['file_size'] = os.path.getsize(media_file['file_path'])  # get file size

    if v >= 3:
        print ("\nOld Order:")
        for media_file in asset_list:
            print (media_file['file_size'])
        print ("_____________________________")

    asset_list = sorted(asset_list, key=get_key_file_size)    # sort our list by file size. smaller first

    if v >= 3:
        print ("\nNew Order:")
    value = 0
    for media_file in asset_list:
        media_file['file_value'] = media_file['file_value'] + value  # add the value based on order in list
        if v >= 3:
            print (media_file['file_size'])
    if v >= 3:
        print ("\n")

    asset_list = sorted(asset_list, key=get_key_file_value)
    return asset_list[0]


# Turn a string frog regex searches into a date in dictionary form
def get_date(date_string):

    replace = "_./"  # what characters to remove that were seperating dates.
    for char in replace:
        date_string = date_string.replace(char, "")

    if len(date_string) == 4:
        date = {'year': date_string, 'month': "", 'day': ""}
    elif len(date_string) == 6:
        date = {'year': date_string[0:4], 'month': date_string[-2:], 'day': ""}
    elif len(date_string) == 8:
        date = {'year': date_string[0:4], 'month': date_string[4:6], 'day': date_string[-2:]}
    else:
        date = {'year': "", 'month': "", 'day': "", 'decade': ""}

    return date


def csv_process(path, v=1):
    # Open the csv file to work on
    if v >= 2:
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
        if v >= 3:
            print ("output of CSV file:")
            for item in jobs_list_clean:
                print (item)
            print ("")
        return jobs_list


def tracker_dict(item):

    dicts = {'source': item[0], 'Copyright': item[1], 'asset_label': item[2], 'date': item[3], 'notes': item[4],
             'link': item[5], 'decade': "", 'dict_date': {'year': "", 'month': "", 'day': ""},  # to store the final date
             'label_dict_date': {'year': "", 'month': "", 'day': ""},  # store date from label
             'field_dict_date': {'year': "", 'month': "", 'day': ""}}  # store date from field
    return dicts


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




def main():

    print("")  # a nice blank space after the user puts in all the input
    # get arguments set up
    unpack = set_argparse()  # returns list of parsed arguments and the parser itself
    #    parser = unpack[0]  # unpack the parser
    args = unpack[1]  # unpack the parsed args

    check_args(args)        # make sure user entered correct input
    v = args.verbosity
    project_id = args.project_id    # user entered project id
    csv_path = args.input   # location of csv file contaiing metadata
    directory = args.directory
    # set up our regular expression match
    pattern_archival = re.compile('RR[1-3]\d\d_A\d+', re.IGNORECASE)  # looks for beginning of asset label pattern
    pattern_vandy = re.compile('RR[1-3]\d\d_[1-2]\d\d\d_\d\d_[0-3]\d_[a-z][a-z][a-z]_A\d+', re.IGNORECASE)  # matches vandy pattern
    pattern_asset_num = re.compile('_A\d{1,3}(_|.)', re.IGNORECASE)
    pattern_date = re.compile('(_|.)[1-2]\d\d\d(.|_)[0-1]\d(.|_)[0-3]\d(.|_)')
    pattern_year = re.compile('(.|_)[1-2]\d\d\d(.|_)')
    pattern_year_month = re.compile('(.|_)[1-2]\d\d\d(.|_)[0-1]\d(.|_)')
    pattern_year_month_euro = re.compile('(.|_)[0-1]\d(.|_)[1-2]\d\d\d(.|_)')
    pattern_date_euro = re.compile('(_|.)[1-2]\d\d\d(.|_)[0-1]\d(.|_)[0-3]\d(.|_)')


    # Create a list to dump everything into
    raw_list = []   # all files under the root and all sub directories specified by the user
    list_first_pass = []    # list after first rudimentary screening
    list_archival_media = []    # screened so all files should be media files in this list
    list_archival_other_projects = []  # media files from other projects
    list_vanderbilt = []  # vanderbilt identified media
    list_vanderbilt_other_projects = []  # Vanderbilt identified media from other projects
    list_duplicated_archival_media = []  # media that has duplicates in user selected project
    list_non_dup_archival_media = []  # media in the user selected project that has no duplicate asset number
    list_tracker_sheet = []     # all the tracker entries that we will match up to a file
    list_errors = []  # to store any errors in. Assets in tracker without matching files, tracker elements < 6

    #  create the raw list of files
    for root, dirs, files, in os.walk(directory):
        for file_local in files:
            item = set_metadata(file_local,os.path.join(root, file_local), v)
            raw_list.append(item)

    # first sort. ignore hidden files and small files
    for unknown_file in raw_list:
        if unknown_file['file_name'][0] != ".":  # This is not a hidden file.
            if os.path.isfile(unknown_file['file_path']):
                file_size = os.path.getsize(unknown_file['file_path'])
                if file_size > 2032933:  # we only want files 2MB and up
                    list_first_pass.append(unknown_file)

    #  Based on retro report naming convention find all the media files
    for media_file in list_first_pass:

        # standard archival match
        if pattern_archival.match(media_file['file_name']):
            # get our asset number
            re_match = pattern_asset_num.search(media_file['file_name'])
            asset = re_match.group(0)  # grab the first match

            #  Strip out unwanted characters to get our asset number
            replace = "_.Aa"  # what characters to remove
            for char in replace:
                asset = asset.replace(char, "")
            asset = int(asset)  # Strip any 0's in front of number
            media_file['asset_number'] = asset  # make it a string again and store

            #  check to see if this belongs to our project
            if project_id.lower() == media_file['file_name'][0:5].lower():
                list_archival_media.append(media_file)
            else:
                list_archival_other_projects.append(media_file)

        # vanderbilt match
        elif pattern_vandy.match(media_file['file_name']):
            # we only want the mpeg files
            if ".mpg" in media_file['file_name'] or ".mpeg" in media_file['file_name']:
                # get our asset number
                replace = "_.Aa"
                re_match = pattern_asset_num.search(media_file['file_name'])
                asset = re_match.group(0)  # grab the first match
                for char in replace:
                    asset = asset.replace(char, "")
                asset = int(asset)
                media_file['asset_number'] = asset

                #  check to see if this belongs to our project
                if project_id.lower() == media_file['file_name'][0:5].lower():
                    list_vanderbilt.append(media_file)
                else:
                    list_vanderbilt_other_projects.append(media_file)

    #  If we found assets, separate unique from assets which have a duplicate
    if len(list_archival_media) > 0:
        unpack = sort_list(list_archival_media)  # this function separates the list into two separate lists
        list_duplicated_archival_media = unpack[0]
        list_non_dup_archival_media = sorted(unpack[1], key=get_key_asset_number)  # sort this list by asset number
    else:
        print ("No Archival Media Found!\nTry another directory")

    if len(list_vanderbilt) > 0:
        if v >= 1:
            print ("Vanderbilt Media found")
            if v >= 2:
                print ("\nVanderbilt Media list:")
                for item in list_vanderbilt:
                    print ("\t" + item['file_path'])

    if len(list_vanderbilt_other_projects) > 0:
        if v >= 1:
            print ("Vanderbilt from other projects found")
            if v >= 2:
                print ("\nVanderbilt from other projects list:")
                for item in list_vanderbilt_other_projects:
                    print ("\t" + item['file_path'])

    if len(list_non_dup_archival_media) > 0:
        if v >= 2:
            print ("\nNon duplicated assets:")
            for item in list_non_dup_archival_media:
                print ("\t" + item['file_path'] + " A: " + str(item['asset_number']))

    if len(list_duplicated_archival_media) > 0:
        if v >= 2:
            print ("\nDuplicated assets:")
            for sublist in list_duplicated_archival_media:
                for media in sublist:
                    print ("\t" + media['file_path'])

        # go through the list, pick the correct file and add to non duplicated list
        for sublist in list_duplicated_archival_media:
            list_non_dup_archival_media.append(choose_file(sublist, v))

    if len(list_non_dup_archival_media) > 0:
        if v >= 2:
            print ("\nNon duplicated assets after adding duplicate list:")
            list_non_dup_archival_media = sorted(list_non_dup_archival_media, key=get_key_asset_number)
            for item in list_non_dup_archival_media:
                print ("\t" + item['file_path'] + " A: " + str(item['asset_number']))

    if len(list_archival_other_projects) > 0:
        if v >= 2:
            print ("\nOther project Media:")
            for item in list_archival_other_projects:
                print ("\t" + item['file_path'])

    # grab the dates from file names
    for media_file in list_non_dup_archival_media:
        re_match = pattern_date.search(media_file['file_name'])  # match for normal date format
        if re_match is not None:
            media_file['dict_date'] = get_date(re_match.group(0))
        else:
            re_match = pattern_year_month.search(media_file['file_name'])  # Year & month
            if re_match is not None:
                media_file['dict_date'] = get_date(re_match.group(0))
            else:
                re_match = pattern_date_euro.search(media_file['file_name'])  # Date Euro format
                if re_match is not None:
                    media_file['dict_date'] = get_date(re_match.group(0))
                else:
                    re_match = pattern_year_month_euro.search(media_file['file_name'])   # Euro format year month
                    if re_match is not None:
                        media_file['dict_date'] = get_date(re_match.group(0))
                    else:
                        re_match = pattern_year.search(media_file['file_name'])  # look for year only
                        if re_match is not None:
                            media_file['dict_date'] = get_date(re_match.group(0))

    for media_file in list_non_dup_archival_media:
        print " Asset: " + str(media_file['asset_number']) + " - " + str(media_file['dict_date'])

    csv_dump = csv_process(csv_path, v)

    for item in csv_dump:

        if len(item) < 6:
            # Not enough elements in this entry. add to errors
            list_errors.append(item)
        else:
            tracker_info = tracker_dict(item)
            re_match = pattern_asset_num.search(tracker_info['asset_label'])
            if re_match is not None:
                asset = re_match.group(0)  # grab the first match
                #  Strip out unwanted characters to get our asset number
                replace = "_.Aa"  # what characters to remove
                for char in replace:
                    asset = asset.replace(char, "")
                asset = int(asset)  # Strip any 0's in front of number
                tracker_info['asset_number'] = asset  # make it a string again and store
                list_tracker_sheet.append(tracker_info)

            else:  # add item to error list because we could not find asset number in label
                list_errors.append(item)

    # extract Dates from our new tracker list
    # date from label first
    for tracker_entry in list_tracker_sheet:
        re_match = pattern_date.search(tracker_entry['asset_label'])  # match for normal date format
        if re_match is not None:
            tracker_entry['label_dict_date'] = get_date(re_match.group(0))
        else:
            re_match = pattern_year_month.search(tracker_entry['asset_label'])  # Year & month
            if re_match is not None:
                tracker_entry['label_dict_date'] = get_date(re_match.group(0))
            else:
                re_match = pattern_date_euro.search(tracker_entry['asset_label'])  # Date Euro format
                if re_match is not None:
                    tracker_entry['label_dict_date'] = get_date(re_match.group(0))
                else:
                    re_match = pattern_year_month_euro.search(tracker_entry['asset_label'])  # Euro format year month
                    if re_match is not None:
                        tracker_entry['label_dict_date'] = get_date(re_match.group(0))
                    else:
                        re_match = pattern_year.search(tracker_entry['asset_label'])  # look for year only
                        if re_match is not None:
                            tracker_entry['label_dict_date'] = get_date(re_match.group(0))

    # Now date field
    for tracker_entry in list_tracker_sheet:
        re_match = pattern_date.search(tracker_entry['date'])  # match for normal date format
        if re_match is not None:
            tracker_entry['field_dict_date'] = get_date(re_match.group(0))
        else:
            re_match = pattern_year_month.search(tracker_entry['date'])  # Year & month
            if re_match is not None:
                tracker_entry['field_dict_date'] = get_date(re_match.group(0))
            else:
                re_match = pattern_date_euro.search(tracker_entry['date'])  # Date Euro format
                if re_match is not None:
                    tracker_entry['field_dict_date'] = get_date(re_match.group(0))
                else:
                    re_match = pattern_year_month_euro.search(tracker_entry['date'])  # Euro format year month
                    if re_match is not None:
                        tracker_entry['field_dict_date'] = get_date(re_match.group(0))
                    else:
                        re_match = pattern_year.search(tracker_entry['date'])  # look for year only
                        if re_match is not None:
                            tracker_entry['field_dict_date'] = get_date(re_match.group(0))

    print "\n\n"
    for tracker_entry in list_tracker_sheet:
        print "Asset: " + str(tracker_entry['asset_number']) + " - Feild date: " + str(tracker_entry['field_dict_date']) + " label Date: " + str(tracker_entry['label_dict_date'])

    print "\nErrors:"
    print list_errors
if __name__ == "__main__":
        main()