# Find the Network drive associated with the story
# Returns Network drive name (may also mount it) if found
# Returns "invalid_asset_label" when asset label is funky
# Returns "did_not_find" when it could not find a network drive associated with the label

import os
from retrosupport.process import volume_result
from retrosupport.process import parse_asset_label

def find_story_volume(asset, verbosity = 1):
    # Detrmine if RR# is an extension ie RR209.02 or an original RR209
    if asset[5] == "_":
        rr_number = asset[:5].lower()
    elif asset[5] == ".":
        rr_number = asset[:8].lower()
    else:
        # In a correct RR number the 6th character (#5 in computer speak, starting with 0) should be a '_' or '.'
        # If its not something is fucked up. Lets let the user know
        print "Asset labels appears to be non standard format"
        print "unable to find story volume..."
        if verbosity >= 2:
            print "Its all your fault"
        return volume_result.invalid_asset_label

    directories = os.listdir("/Volumes")  # get a list the directories in /volumes
    volumes = []  # to store actual volumes

    # Go through each directory. Check if they are mount points and exclude any with "MEDIA"
    # in title. These are avid media mounts and are not desired. Only grab volumes with the RR# also
    for directory in directories:
        path = "/Volumes/" + directory  # get the full path to the directory
        if not "MEDIA" in path and rr_number[:5] in path.lower():  # We don't want any Avid Media Mounts
            if os.path.ismount(path):  # checking if directory is a mount
                volumes.append(path)  # This is a mount point, Add to list

    if len(volumes) == 1:  # one mountpoint found. Check and see if its legit
        if is_story(volumes[0], rr_number):
            # We have found our story drive
            return volumes[0]

    elif len(volumes) > 1:  # found multiple potential volumes. sort through them
        for volume in volumes:
            if rr_number in volume:  # check and see if the rr# matches
                if is_story(volume, rr_number): # check and see if its a story volume
                    print volume
                    return volume  # we found it. This logic matches the first pattern. But should be the only one

        # now just check for partial matches, in case its a .02 number and we are going to original volumls e
        for volume in volumes:
            if is_story(volume, rr_number): # check and see if its a story volume
                if verbosity >= 1:
                    print volume
                return volume  # we found it. This logic matches the first pattern. But should be the only one
        # At this point we found multiple mount points with our RR number
        # However none match the pattern of what they should look like. Return an error
        return volume_result.not_found

    else:
        print "Could not find a mounted volume associated with your asset label"
        return volume_result.not_found

    return volume_result.not_found  # for good measure. in case the function gets to the end for some reason


# checks and see's if the path is leading to an RR Story Drive.
# Returns True if its a story drive False if its not. Based on a good guess
def is_story(path, rr_number="na"):

    contents_raw = os.listdir(path)  # list directories (and files) in potential story drive
    contents = []   # list to store just directories

    # just get the directories now
    for item in contents_raw:
        check = path + "/" + item # create path to check
        if os.path.isdir(check): # test and see if the path leads to a directory
            contents.append(item.lower())  # add directory to our list

    # our reference list to compare to
    reference = ["_ARCHIVAL_FOOTAGE", "_EDIT_PROJECT_FILE_BACKUPS", "_GRAPHICS", "_MIX", "_MUSIC"
        , "_NARRATION", "_ORIGINAL_FOOTAGE", "_OUTPUTS", "_PACKAGING", "_SCREENERS", "_SFX", "_STILLS_DOCS_HEADLINES"]
    shared_elements = 0 # counter to see how many directories we have in common

    # do the comparison
    if rr_number == "na": # no rr number specified,
        print "No RR number given for comparison"
        print "Using Generic Compare"

        for directory in contents:
            if directory[5:] in reference:
                shared_elements = shared_elements + 1   # incriment the number of shared elements

    else:   # RR number specified
        # put the RR number in all the refference strings
        rr_number_reference = [] # net list to hold new reference
        for item in reference:
            new_string = rr_number.lower() + item.lower()
            rr_number_reference.append(new_string)

        # now do the comparison
        for directory in contents:
            if directory in rr_number_reference:
                shared_elements = shared_elements + 1   # incriment the number of shared elements

    if shared_elements > 6: # 6 is the threashhold. If only 6 matches its not a story drive. More than 6 it is
        return True

    return False


def find_google_drive_archival(google_drive_path, story_folder_path, rr_number, verbosity = 1):

    path = google_drive_archival_search(story_folder_path, rr_number)  # get our archival location
    if path == volume_result.not_found:
        path = google_drive_archival_search(google_drive_path, rr_number) # try root of the google drive
        if path == volume_result.not_found:  # still can't find the archival folder
            return volume_result.not_found
        else:   # we found it on the second try
            return path
    else:   # we found the path on the first try
        return path


def google_drive_archival_search(target_volume, rr_number):

    directory_list = os.listdir(target_volume)  # list contents in path
    directories = [] # to put directories in
    path = volume_result.not_found   # where we put our final path if found

    # go through list to sort out the directories
    for item in directory_list:
        if os.path.isdir(target_volume + "/" + item): # test and see if the path leads to a directory
            directories.append(item)  # add directory to our list

    # find the directory with our rr number
    for item in directories:
        if rr_number.upper() in item:
            # found our directory. Build a path to its archivel screeners folder
            path = target_volume + "/" + item + "/" + rr_number.upper() + \
                    "_ARCHIVAL/" + rr_number.upper() + "_SCREENERS_ARCHIVAL/"
            return path

    return path  # this should never need to be executed but..


def find_archival_location(target_volume, rr_number="na"):

    # make sure target_volume is a valid path
    if not os.path.exists(target_volume):
        print "Error.\n Path send to function 'find_archival_location' does not exist."
        return volume_result.not_found

    # no RR number specified. Try and get it from target_volume. This doesn't work yet
    if rr_number == "na":
        rr_number = target_volume[0:5]

    root_list = os.listdir(target_volume)  # list contents in path
    root_directories = [] # to put directories in
    # go through list to sort out the directories
    for item in root_list:
        if os.path.isdir(target_volume + "/" + item): # test and see if the path leads to a directory
            root_directories.append(item)  # add directory to our list

    # get our strings to match for
    # this method will get the first match and ignore all others
    prefix_2 = rr_number.lower() + "_archival"
    prefix = rr_number.lower() + "_archival_footage"
    target = "notfound"  # the check. Once this changes no more compares are made and it stores /
                            # the directory we are looking for

    # Go Through all the directories and look for our strings
    # this will stop at the first hit. however there should
    # only be one "archival" directory in a retro volume
    # this should not produce any undesired results
    for directory in root_directories:
        if target == "notfound":
            if prefix in directory.lower() or prefix_2 in directory.lower():
                target = target_volume + "/" + directory + "/"

    if target == "notfound":
        print "Could not find archival folder. Sorry"
        return volume_result.not_found
    else:
        return target

    # just to cover ourselves
    return volume_result.not_found


def update_volumes():
    """
    this function updates the list of valid editshare
    media drives
    :return:
    """
    print 'do something useful here'

def google_drive(verbosity):
    """
    this function checks to see if the Google Drive
    is mounted on the computer. Returns path of google drive down and the Story Folders
    :return: List
    """

    # Paths to check
    google_drive_path = "/Volumes/Google_Drive"
    story_path = google_drive_path + "/_RETRO_SHARED/STORY_FOLDERS"
    list = []   # where to store the return strings

    if os.path.ismount(google_drive_path):
        if os.path.isdir(story_path):
            list.append(volume_result.found)
            list.append(google_drive_path)
            list.append(story_path)
            return list   # we found both paths so return them
        else:
            if verbosity >= 2:
                print ("Google Drive is mounted however I cannot find the story path")
                print ("Thats not right")
            list.append(volume_result.not_found) # we did not find the story folder path, make as failed
            return list
    else:
        if verbosity >=2:
                print ("Google Drive does not appear to be mounted")
                print ("perhaps you should mount it.")
        list.append(volume_result.not_found)
        return list             # "we ain't find it"


def find_asset(asset, location):

    # list all the items in the location
    dir_list = os.listdir(location)
    file_list = []  # where we will hold just the files
    file_found_list = []    # where we will hold all the files that have the name we are looking for

    # process the list
    for item in dir_list:
        path = location + item  # built the full path toward the item

        # if its a file add it to our list. Leave dirs behind
        if os.path.isfile(path):
            file_list.append(item)

    # now search for our filename
    for item in file_list:
        if asset in item:
            file_found_list.append(item)

    return file_found_list

def main():
    print ("Can't be run as main()")

if __name__ == "__main__":
    main();