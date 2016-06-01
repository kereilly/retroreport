#!/usr/bin/env python
## rrdownloader
## downloads media from a website and puts
## all files where they should be properly
## labeled. For Archival footage only. Also
## will make a screener if google drive is present
## version 2.0 5/29/2016

# Stuff to import
import sys
import os
import subprocess
import time
from youtube_dl import YoutubeDL
from retrosupport.locate import find_story_volume
from retrosupport.locate import find_archival_location
from retrosupport.locate import parse_asset_label
from retrosupport.locate import google_drive
from retrosupport.locate import find_google_drive_archival
from retrosupport.media import create_screener

# Global Variables
global download_target

def check_youtubedl():
    """
    checks to see if youtube_dl is present
    :return:
    """
    print 'check for youtube_dl here'

# Logger for youtube-dl
class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

# this function runs when youtube_dl is working to get status info
def my_hook(d):

    # lets give the user some feedback
    if d['status'] == 'downloading':
        speed =  "Download Speed: " + str(int(d['speed']/1024)) + " kb/s"
        eta =  "   ETA: " + str(d['eta'])
        text = "\r" + speed + eta
        sys.stdout.write(text)
        sys.stdout.flush()

    # well it finished so tell the user that and store file location
    if d['status'] == 'finished':
        print("\nI've Done it! Your video has been downloaded!")
        print "Or at least part of it if its in multiple chunks\n"
        filelocation = d['filename']

    if d['status'] == 'error':
        print "Well something has gone wrong with the download"
        print "sorry"
        exit()

def download_video(url, archival_location, asset):
    """
    calls youtube_dl to download the file
    :param url: url of file to download
    :param archival_location: where to save file
    :param asset: asset number to append to file
    :return:
    """

    # Use global variable to get the download location
    global download_target
    download_target = "none"
    # Put Location and filename to save in a variable
    destination = archival_location + asset + ".%(ext)s"
    # options for youtubedl
    ydl_opts = {
        'logger' : MyLogger(),
        'progress_hooks': [my_hook],
        'outtmpl' : destination,
        'ignoreerrors' : True
    }
    try:
        # Lets download it now
        with YoutubeDL(ydl_opts) as ydl:
            print "Extracting information about the file to download"
            info = ydl.extract_info(url, download=False)
            download_target = ydl.prepare_filename(info)
            print "Target download location: " + download_target
            ydl.download([url])
            print ""
    except:
        print "Error with downloader. Most likely Unsupported URL"
        # Exit the program
        exit()

# call youtube-dl from command line. No need to use it. just keeping it here
def download_video_externaly(url, archival_location, asset):

    # Build the command
    ext = "%(ext)s"
    cmd = 'youtube-dl %s -o "%s%s.%s"' % (
        url, archival_location, asset, ext)

    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            )

    youtube_dl = proc.communicate()[0]
    print youtube_dl


    # progress bar for ffmpeg output
def update_progress(progress):

    barLength = 40 # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(barLength*progress))
    text = "\rPercent: [{0}] {1}% {2}".format( "#"*block + "-"*(barLength-block), progress*100, status)
    sys.stdout.write(text)
    sys.stdout.flush()

def instructions():
    print "\ninstructions:"
    print "This program is for downloading media to the server on the appropriate story space"
    print "It will also make a screener and upload to the google drive\n"
    print "Usage:"
    print '"rrdownloader assetlabel url"'
    print 'The asset label cannont have spaces or " in the title'

def check_arg(argv):

    # If user asked for help or supplied no arguments
    if len(argv) == 1:
        instructions()
        exit()
    toupdate = str(argv[1].lower())
    if toupdate == "update":
        update()
    if argv[1].lower() == "help":
        instructions()
        exit()
    # if more than three arguments given
    if len(argv) >= 5:
        print "too many options. Ignoring everything after " + "'" + argv[4] + "'"
    if len(argv) >= 4:
        if argv[3].lower() != "yadif":
            print argv[3] + " invalid option! Ignoring"

    if "c-span.org" in argv[2].lower():
        print "\nWARNING!!!!"
        print "C-span clips must be check after downloading"
        time.sleep(1)
        print "The website changes often and can break the downloader"
        print "You may not have the clip you want"
        print "If it fails try updating youtube_dl\n"
        time.sleep(2)

def about():

    print "\nrrdownloader version 2.0 - beta"

def main():

    about()
    check_arg(sys.argv) # check user input
    asset = sys.argv[1] # put our asset in a variable
    url = sys.argv[2]   # put the url in a variable
    #check_url(url)      # check to see if the url is valid

    # extract the RR Number and Asset Number from the asset label
    unpack = parse_asset_label(asset)
    rr_number = unpack[0]
    asset_number = unpack[1]

    # get the story volume
    volume = find_story_volume(asset)
    # check to see if we got our story volume
    if volume == "did_not_find":
        print "Unable to locate story volume" \
              "\nPlease mount it from editshare and try again"
        exit()
    elif volume == "invalid_asset_label":
        print "Asset label is not in our standard format" \
              "\nPlease check it and try again"
        exit()
    else:
        # we have succsess
        print "Story Volume location: " + volume

    # find archival directory
    archival_location = find_archival_location(volume, rr_number)
    # Check to see if we found it
    if archival_location == "did_not_find":
        print "Unable to locate 'Archival_Footage' directory" \
              "\nPlease check the story drive and try again"
        exit()
    else:
        print "Archival path is: " + archival_location + "\n"

    # ready to download the video
    print "Working on asset: " + asset_number
    download_video(url, archival_location, asset) # call a function that uses youtube-dl

    # Check to see if we downloaded the file
    file_target = ""
    if download_target == "none":
        # youtube-dl never even got a potential file name. Exit the program
        print "We were not able to download this video" \
              "\nGoodbye"
        exit()
    elif os.path.isfile(download_target):
        # youtube-dl got the file. Lets continue
        print "We have sucsessfully downloaded the file"
        file_target = download_target
    else:
        # youtube-dl got a file name but we don't see it. Find it!
        print "Can't find the file that was supposed to have been downloaded" \
              "\nffmpeg probably had to mux it" \
              "\nI'm looking for it"

        # list all the items in the archival footage location
        dir_list = os.listdir(archival_location)
        file_list = [] # where we will hold just the files
        file_found_list = []    # where we will hold all the files that have the name we are looking for

        # process the list
        for item in dir_list:
            path = archival_location + item # built the full path toward the item

            # if its a file add it to our list. Leave dirs behind
            if os.path.isfile(path):
                file_list.append(item)

        # now search for our filename
        for item in file_list:
            if asset in item:
                file_found_list.append(item)

        # now check the results
        if len(file_found_list) == 0:
            print "Cannont find our file" \
                  "\nSorry man :("
            exit()
        elif len(file_found_list) > 1:
            print "For some reason i see this asset label: " + asset
            print "In more than one file at our download location: " + archival_location
            print file_found_list
            print "THIS CANNOT BE!"
            exit()
        else:
            file_target = archival_location + file_found_list[0]
            print "Found the file! " + file_target + "\n"

    # now for the screener stuff

    # check if the google drive is present
    google_drive_path = google_drive()
    if google_drive_path == "did_not_find":
        print "The Retro Report Google Drive does not appear to be mounted"
        print "Not making any screeners for you"
        exit()
    else:
        print "Google Drive is mounted"

    # find the location of the story folder archival we want
    screener_path = find_google_drive_archival(rr_number)
    if screener_path == "did_not_find":
        # we couldn't find the screener location
        print "Could not find story folder in google drive"
        print "no screeners made"
        exit()
    else:
        print "Screener location found: " + screener_path

    #add asset label to path
    screener_path = screener_path + asset
    # create the screener
    create_screener(file_target, screener_path)


    # say goodbye
    print "\nThanks for using rrdownloader. Have a nice day\n"
    exit()

if __name__ == "__main__":
    main();
