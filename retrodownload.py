#!/usr/bin/env python

import sys
import os
import subprocess
import time
import argparse
from retrosupport.locate import find_story_volume
from retrosupport.locate import find_archival_location
from retrosupport.locate import google_drive
from retrosupport.locate import find_google_drive_archival
from retrosupport.locate import find_asset
from retrosupport.media import create_screener
from retrosupport.media import getinfo
from retrosupport.media import ffmpeg
from retrosupport.process import volume_result
from retrosupport.process import download_result
from retrosupport.process import resolution_type
from retrosupport.process import to_trim
from retrosupport.process import formats
from retrosupport.process import parse_asset_label
from retrosupport.retro_dl import retro_youtube_dl



# a class to create enums
# Used for checking user arguments
class selection(object):
    wrong = 0
    single = 1
    single_specific = 2
    batch = 3

def check_args(args):
    # in verbose mode show arguments
    if args.verbosity >= 2:
        print "\nOUTPUT OF ARGPARSE:"
        print str(args) + "\n"

    # Check for user argument errors
    # check for exclusive single download
    if (args.asset_label != None or args.url != None) and args.download != None:
        print "\nYou cannot use the -d option with either -u or -a. They must be used exclusevly"
        if args.verbosity >=2:
            print "Come on... You can do better!"
        print ""    # Make empty line. For pretty formatting
        return selection.wrong

    # check for batch download and single download options
    if (args.asset_label != None or args.url != None or args.download != None
        ) and (args.batch != None or args.multi_thread != False or args.output_file != None):
        print "\nYou can not specify single download options and batch download options at the same time"
        if args.verbosity >=2:
            print "Stupid Ass Fuck!\n"
        return selection.wrong

    if (args.batch != None and args.trim != None):
        if args.verbosity >=2:
            print "Trim option does not work with batch download. Ignoring:"
            print args.trim

    # All is well with arguments. Let user know if verbosity dictates
    if args.verbosity >=2:
        print "User arguments checked by 'check_args'. All is well\n"

    # now figure out what option user selected and return it
    if args.download != None:
        return selection.single   # user is using 'rrdownloader' mode
    if args.url != None and args.asset_label != None:
        return selection.single_specific
    if args.batch != None:
        return selection.batch
    else:
        print "Please check your options"
        return selection.wrong

    # this function is going to be responsible for downloading the video
def download_video(asset, url, verbosity = 1, locations = ["none"]):

    # Check to see if we have our locations. If not find them
    if locations[0] == "none":
        # extract the RR Number and Asset Number from the asset label
        unpack = parse_asset_label(asset)
        rr_number = unpack[0]
        asset_number = unpack[1]

        # get the story volume
        volume = find_story_volume(asset)

        # check to see if we got our story volume
        if volume == volume_result.not_found:
            print "Unable to locate story volume" \
                  "\nPlease mount it from editshare and try again"
            return download_result.download_failed
        elif volume == volume_result.invalid_asset_label:
            print "Asset label is not in our standard format" \
                  "\nPlease check it and try again"
            return download_result.download_failed
        else:
            # we have succsess
            if verbosity >= 1:
                print "Volume location found"
            if verbosity >= 2:
                print "Story Volume path is: " + volume

        # Get the archival location
        archival_location = find_archival_location(volume, rr_number)

        # Check to see if we found it
        if archival_location == volume_result.not_found:
            print "Unable to locate 'Archival_Footage' directory" \
                "\nPlease check the story drive and try again"
            return download_result.download_failed
        else:
            # we found the location
            if verbosity >= 1:
                print "Archival location found"
            if verbosity >= 2:
                print "Archival path is: " + archival_location + "\n"

        # Locations set. let the user know what RR number this is
        # Asset number displayed after Locations == "none" if statment
        # So as not to repeat RR number over in batch download
        if verbosity >= 1:
            print "Working on: " + rr_number

    else:   # Locations were specified. Lets check them
        if not os.path.isdir(locations[0]): # Check volume path
            print "Error. Downloader Unable to find story volume location"
            if verbosity >= 2:
                print "Volume path passed to 'download_video' funcion is not valid:"
                print locations[0]
            return download_result.download_failed
        if not os.path.isdir(locations[1]): # Check archival directory path
            print "Error. Downloader unable to find archival directory location"
            if verbosity >= 2:
                print "Archival directory path passed to 'download_video' function is not valid:"
                print locations[1]
            return download_result.download_failed

        # Locations check out thus far. set them in a more friendly variable
        volume = locations[0]
        archival_location = locations[1]

    # ready to download the video
    # let the user know what asset we are working on
    if verbosity >= 1:
        print "Working on asset: " + asset_number

    # Download file and store results
    result = retro_youtube_dl(url, archival_location, asset, verbosity)

    # Return results
    return result

def set_argparse():

     # Start things off using pythons argparse. get user input and give help information
    parser = argparse.ArgumentParser(
        description="The Retro Report Downloader Version 1.0",
        epilog="And that's how you'd foo a bar"
    )
    # Group arguments for single download
    group_single = parser.add_argument_group("Single Download", "Arguments for downloading a single file")
    group_single.add_argument("-d", "--download", type=str, nargs=2,
                              help="Download one file. Asset label followed by URL")

    group_single.add_argument("-a", "--asset-label", type=str,
                              help="Specifically specify asset label. Must also use -u for this method")

    group_single.add_argument("-u", "--url", type=str,
                              help="Specifically specify url. Must also use -a for this method")

    group_single.add_argument("-t", "--trim", type=str, nargs=2,
                        help="In and out point to trim clip. Integers only no :'s. ex 001123 001201 " \
                             "Zero hours, eleven minutes, twentythree seconds to zero hours, twelve...etc " \
                             "In and out points will be padded with 0's in the front until they are 6 digits")

    # Group arguments for batch download
    group_batch = parser.add_argument_group("Batch Download", "Arguments for Batch Downloading")
    group_batch.add_argument("-b", "--batch", type=str,
                             help= "Specify a CSV file for batch download")
    group_batch.add_argument("-m", "--multi-thread", action="store_true", help="Enable multi-threaded downloads")
    group_batch.add_argument("-o", "--output-file", type=str,
                             help="Specify output file to save to. Will be overwritten "
                                  "if it already exists. Or maybe i'll just add a number. Hmmmm.")
    # now regular arguments
    parser.add_argument("-v", "--verbosity", type=int, default=1, choices=[0, 1, 2, 3],
                        help="Increase, 2, or decrease, 0, the level of output. 3 is debug mode. Default is 1")

    # have argparse do its thing
    args = parser.parse_args()

    # pack up what we need to bring back to main
    pack = (parser, args)
    return pack

def check_encoding(file_path, verbosity = 1):

    # our non avid supported containers
    list = ["mkv", "flv", "mpg", "mpeg", "wmv", "webm"]

    # Process string to strip out extension
    string_index = file_path.rfind(".") + 1
    extension = file_path[string_index:]

    # Get information about the file to determine format
    media_info = getinfo(file_path)

    if extension in list:   # This particular extension is in our non avid supported list.
        if verbosity >= 2:
            print "File is in an unnacaptable wrapper: " + extension
            print "These extentions will be re-wrapped:"
            for item in list:
                print item

        # Get pixels of our image into variables
        width = int(media_info['width'])
        height = int(media_info['height'])

        if width <= 720 and height <= 486:     # Check for NTSC format
            if verbosity >= 2:
                print "\nVideo will fit a NTSC SD resolution raster."
                print str(width) + ":" + str(height)
                print "Some additional information about our file:\n"
                for key, value in media_info.iteritems():
                    print str(key) + ":" + str(value)
                print "" # Blank line after the loop

            list = [resolution_type.ntsc, media_info]
            return list

        elif width <= 720 and height <= 576:    # check for PAL
             if verbosity >= 2:
                print "\nVideo will fit a PAL resolution raster."
                print "Some additional information about our file:\n"
                for key, value in media_info.iteritems():
                    print str(key) + ":" + str(value)
                print "" # Blank line after the loop
             list = [resolution_type.pal, media_info]
             return list

        elif width <= 1280 and height <= 720:
            if verbosity >= 2:
                print "\nVideo will fit a 1280:720 HD resolution raster."
                print "Some additional information about our file:\n"
                for key, value in media_info.iteritems():
                    print str(key) + ":" + str(value)
                print "" # Blank line after the loop
            list = [resolution_type.hd_low, media_info]
            return list

        elif width <= 1920 and height <= 1080:
            if verbosity >= 2:
                print "\nVideo will fit a 1920:1080 HD resolution raster."
                print "Some additional information about our file:\n"
                for key, value in media_info.iteritems():
                    print str(key) + ":" + str(value)
                print "" # Blank line after the loop
            list = [resolution_type.hd_high, media_info]
            return list

    else:
        if verbosity >= 2:
            print "File does not need to be re-encoded"
            print "Some additional information about our file:\n"
            for key, value in media_info.iteritems():
                    print str(key) + ":" + str(value)
            print "" # Blank line after the loop

        list = [False, media_info]  # don't need to encode so set first element to false
        return list

def check_download_result(results, asset):
    # Check for all the bad things first, then continue
        if results == download_result.download_failed:
            print "The download failed for whatever reason"
            return False
        elif results == download_result.multiple_file_found:
            print "Multiple files of the same asset were found"
            print "Cannot continue"
            return False
        elif results == download_result.file_not_found:
            print "Could not find the file Youtube_Dl downloaded"
            print "Cannot continue"
            return False
        elif results == download_result.invalid_asset_label:
            print "The Asset label: " + asset + "is not valid"
            print "Cannot continue"
            return False
        elif os.path.isfile(results):
            # Further process the file
            return True
        else:
            print "Not sure if you file was downloaded or not but"
            print "I am sure you have no screener!"
            return False
    # Shouldn't need this but just for good measure
        return False

def post_download_process(download_result, trim, verbosity = 1):

    source_file_path = download_result # it might not be the source file path but there are checks in place
    index = source_file_path.rfind(".") # to index where the extention starts

    # check to see if we need to re-encode
    encode = check_encoding(download_result, verbosity)
    media_info = encode[1]

    if encode[0] == False:
        if verbosity >= 2:
            print "File is in Avid friendly format. No need to re-encode"

        if trim[0] == to_trim.false:
            if verbosity >= 2:
                print "No trim option selected, leaving file as is"
            return [False, to_trim.false, source_file_path]
        else:
            if verbosity >= 1:
                print "File set to be trimmed: " + trim[0] + " to " + trim[1]
            # rename file for destination path
            dest = source_file_path[:index] + "_Trimmed" + source_file_path[index:]
            final_path = ffmpeg(source_file_path, dest, media_info, resolution_type.ntsc, trim, verbosity, formats.copy) # resolution type does not mater if formats is copy
            return [False, to_trim.true, final_path]
    elif encode[0] == resolution_type.ntsc:
        # Check for trim option
        if trim[0] == to_trim.false:
            if verbosity >= 1:
                print "Encoding file into IMX50 format in MXF wrapper for fast Avid import"
            dest = source_file_path[:index] + ".mxf"
            ffmpeg(source_file_path, dest, media_info, resolution_type.ntsc, trim, verbosity, formats.imx50)
            return [formats.imx50, to_trim.false, source_file_path]
        else:
            if verbosity >= 1:
                print "Encoding file into IMX50 format in MXF wrapper for fast Avid import"
                print "and trimming from: " + trim[0] + " to " + trim[1]
            dest = source_file_path[:index] + "_Trimmed.mxf"
            final_path = ffmpeg(source_file_path, dest, media_info, resolution_type.ntsc, trim, verbosity, formats.imx50)
            return [formats.imx50, to_trim.true, final_path]
    elif encode[0] == resolution_type.pal:
         # Check for trim option
        if trim[0] == to_trim.false:
            if verbosity >= 1:
                print "Encoding file into IMX50 format in MXF wrapper for fast Avid import"
            dest = source_file_path[:index] + ".mxf"
            ffmpeg(source_file_path, dest, media_info, resolution_type.pal, trim, verbosity, formats.imx50)
            return [formats.imx50, to_trim.false, source_file_path]
        else:
            if verbosity >= 1:
                print "Encoding file into IMX50 format in MXF wrapper for fast Avid import"
                print "and trimming from: " + trim[0] + " to " + trim[1]
            dest = source_file_path[:index] + "_Trimmed.mxf"
            final_path = ffmpeg(source_file_path, dest, media_info, resolution_type.pal, trim, verbosity, formats.imx50)
            return [formats.imx50, to_trim.true, final_path]
    elif encode[0] == resolution_type.hd_high or resolution_type.hd_low:
        # Check for trim option
        if trim[0] == to_trim.false:
            if verbosity >= 1:
                print "Encoding file into XDCAM422 format in MXF wrapper for fast Avid import"
            dest = source_file_path[:index] + ".mxf"
            ffmpeg(source_file_path, dest, media_info, resolution_type.hd_high, trim, verbosity, formats.xdcam422)
            return [formats.xdcam422, to_trim.false, source_file_path]
        else:
            if verbosity >= 1:
                print "Encoding file into XDCAM422 format in MXF wrapper for fast Avid import"
                print "and trimming from: " + trim[0] + " to " + trim[1]
            dest = source_file_path[:index] + "_Trimmed.mxf"
            final_path = ffmpeg(source_file_path, dest, media_info, resolution_type.hd_high, trim, verbosity, formats.xdcam422)
            return [formats.xdcam422, to_trim.true, final_path]
    else:
        if trim[0] == to_trim.true: # couldn't figure out the resolution of file. Just trim for heck of it.
            dest = source_file_path[:index] + "_Trimmed" + source_file_path[index:]
            final_path = ffmpeg(source_file_path, dest, media_info, resolution_type.ntsc, trim, verbosity, formats.copy) # resolution type does not matter when formats is set to copy
            return [False, to_trim.true, final_path]

    # This should never be executed.
    if verbosity >= 1:
        print "Post_Process_Function is unsure of what to do. Leaving file as is"
    return [False, to_trim.false, source_file_path]

def screener_process(source, asset, trimmed, verbosity):
    print "\n Sceener Functions Follow\n\n"
    list = google_drive(verbosity)
    # check and see if we found the google drive
    if list[0] == volume_result.not_found:
        if verbosity >= 1:
            print "No screener will be made"
            print "Cannot find the Google Drive story path" \
                  "\nCheck to see if Google Drive is mounted"
        return False
    else:
        # unpack google path list
        google_drive_path = list[1]
        story_folder_path = list[2]

        list = parse_asset_label(asset)
        rr_number = list[0]     # unpack asset list

        if verbosity >= 1:
            print "Google Drive found at: " + google_drive_path
            print "Story Folders found at: " + story_folder_path

    # find the location of the story folder archival we want
    screener_path = find_google_drive_archival(google_drive_path, story_folder_path, rr_number, verbosity)
    if screener_path == volume_result.not_found:
        # we couldn't find the screener location
        if verbosity >= 1:
            print "Could not find story folder in google drive for: " + rr_number
            print "No screeners will be Made"
            return False
    else:
        if verbosity >= 1:
            print "Screener location found: " + screener_path

    # find all files in our google drive location that have our asset number
    file_found_list = find_asset(asset, screener_path)

        # now check the results
    if len(file_found_list) == 0:
    # no previous screener. go ahead and make one

        #add asset label to path
        screener_path = screener_path + asset

        # check for trimming
        if trimmed:
            screener_path = screener_path + "_Trimmed"

        # create the screener
        print "\nScreener media source:"
        print source
        create_screener(source, screener_path, verbosity)
        return True
    else:
        if verbosity >= 1:
            print "Looks like a screener already exists or there are duplicate asset #'s"
        return False
def main():


    print "" # a nice blank space after the user puts in all the input
    # get arguments set up
    unpack = set_argparse() # returns list of parsed arguments and the parser itself
    parser = unpack[0]  # unpack the parser
    args = unpack[1]    # unpack the parsed args
    verbosity = args.verbosity

    # check Arguments to make sure they are kosher
    argument_result = check_args(args)

    # See if the user doesn't know what uptions to use
    if argument_result == selection.wrong:
        parser.print_help()
        exit()

    # We have the users selection. Lets get stuff done
    # Single download:
    if argument_result == selection.single or selection.single_specific:

        # Figure out which type of single download
        if argument_result == selection.single: # single download. Call downloader and pass one asset and url
            asset = args.download[0]
            url = args.download[1]
            print "We are in test mode"
        if argument_result == selection.single_specific:
            asset = args.asset_label
            url = args.url

        # Download the file and store results
        download = download_video(asset, url, verbosity)


        if verbosity >= 3:
            print "download result code: " + str(download)

        if not check_download_result(download, asset):
            # Download failed
            print "Somthing is wrong. File might have downloaded but no screener made"
            exit()
        else:
            # success lets keep going
            if args.trim == None:
                trim = [to_trim.false] # keep as list since the argparse for trim is a list
            else:
                trim = args.trim
            # Further process the file if nessesary, trim, re-encode etc.
            post_result = post_download_process(download, trim, verbosity)

            if verbosity >= 3:
                print post_result
            # unpack post_result
            format = post_result[0]
            trimmed = post_result[1]
            final_path = post_result[2]
            if verbosity >= 2:
                if trimmed:
                    if format != False:
                        print "Your Media was trimmed and formatted for Avid."
                    else:
                        print "Your file was trimmed."
                else:
                    if format != False:
                        print "Your Media was formatted for Avid"

            # Lets take care of the google drive screener stuff
            screener_result = screener_process(final_path, asset, trimmed, verbosity)

            print screener_result







if __name__ == "__main__":
    main();