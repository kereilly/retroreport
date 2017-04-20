from __future__ import unicode_literals
# Supporting module for rrdownloader

from youtube_dl import YoutubeDL
import sys
import os
from retrosupport.process import download_result
from retrosupport.locate import find_asset


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
        # check and make sure 'speed' is not None. It can be sometimes
        if d['speed'] is not None:
            speed = u"Download Speed: {0} kb/s".format(str(int(d['speed'] / 1024)))
        else:
            speed = "Download Speed not available"
        # just in case do same with ETA
        if d['eta'] is not None:
            eta = "   ETA: " + str(d['eta'])
        else:
            eta = "ETA not available"
        text = "\r" + speed + eta
        sys.stdout.write(text)
        sys.stdout.flush()

    # well it finished so tell the user that and store file location
    if d['status'] == 'finished':
        print("\nI've Done it! Your video has been downloaded!")
        print ("Or at least part of it if its in multiple chunks\n")
        #  filelocation = d['filename']

    if d['status'] == 'error':
        print ("Well something has gone wrong with the download")
        print ("sorry")


def retro_youtube_dl(url, directory_location, asset, verbosity=1):
    """
    calls youtube_dl to download the file
    :param url: url of file to download
    :param directory_location: where to save file
    :param asset: asset number to append to file
    :param verbosity: Level of output for user
    :return: result: String of the end result
    """

    # Put Location and filename to save in a variable
    destination = directory_location + asset + ".%(ext)s"

    # options for youtube-dl
    ydl_opts = {
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
        'outtmpl': destination,
        'ignoreerrors': True,
    }
    try:
        # Lets download it now
        with YoutubeDL(ydl_opts, verbosity) as ydl:
            if verbosity >= 1:
                print ("Extracting information about the file to download")
            info = ydl.extract_info(url, download=False)
            download_target = ydl.prepare_filename(info)
            if verbosity >= 1:
                print ("\nTarget download location: " + download_target)
            ydl_results = ydl.download([url])
            if verbosity >= 2:
                print ("\nThe output of ydl_results follows:")
                print (ydl_results)

    except:
        if verbosity >= 2:
            print ("Error with downloader. Most likely Unsupported URL")
        # return error
        return download_result.download_failed

    # We should have succcess. Get/Confirm file location
    result = process_dl_result(download_target, directory_location, asset, verbosity)

    # Check to see what to return to calling function
    if result == download_result.file_not_found:
        return download_result.file_not_found   # Could not locate what was supposed to have been download
    elif result == download_result.multiple_file_found:
        return download_result.multiple_file_found  # More than one media asset exists
    elif result == download_result.download_failed:
        return download_result.download_failed
    elif os.path.isfile(result):
        return result   # This should be the path to our file
    else:
        return download_result.download_failed


# Figure out if we got the file. search for it if it was muxed
def process_dl_result(download_target, directory_location, asset, verbosity=1):

    # Check to see if we downloaded the file
    if os.path.isfile(download_target):
        # youtube-dl got the file. Lets continue
        if verbosity >= 2:
            print ("\nFile was not muxed by Youtube_Dl")
        file_target = download_target
    else:
        # youtube-dl got a file name but we don't see it. Find it!
        if verbosity >= 2:
            print ("\nCan't find the file that was supposed to have been downloaded."
                   " Youtube_Dl probably had to mux it"
                   "\nI'm looking for it")

        # find all files in our directory location that have our asset number
        file_found_list = find_asset(asset, directory_location)

        # now check the results
        if len(file_found_list) == 0:
            if verbosity >= 2:
                print ("Cannont find any file in directory location: " + directory_location +
                       " with our file name:\n" + asset)
            return download_result.file_not_found

        elif len(file_found_list) > 1:
            print ("For some reason i see this asset label: " + asset)
            print ("In more than one file at our download location: " + directory_location)
            if verbosity >= 2:
                print (file_found_list)
            print ("THIS CANNOT BE!")
            return download_result.multiple_file_found

        else:
            file_target = directory_location + file_found_list[0]
            if verbosity >= 1:
                print ("Found the file! " + file_target)

    return file_target
