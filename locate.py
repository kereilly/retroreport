# Find the Network drive associated with the story
# Returns Network drive name (may also mount it) if found
# Returns "invalid_asset_label" when asset label is funky
# Returns "did_not_find" when it could not find a network drive associated with the label

import os

def find_story_volume(asset):
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
        print "Its all your fault"
        return "invalid_asset_label"

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
        if is_story(volumes[0], rr_number[:5]):
            # We have found our story drive
            return volumes[0]

    elif len(volumes) > 1:  # found multiple potential volumes. sort through them
        for volume in volumes:
            if is_story(volume, rr_number[:5]):
                print volume
                return volume  # we found it. This logic matches the first pattern. But should be the only one
        # At this point we found multiple mount points with our RR number
        # However none match the pattern of what they should look like. Return an error
        return "did_not_find"

    else:
        print "Could not find a mounted volume associated with your asset label"
        return "did_not_find"

    return "did_not_find"  # for good measure. in case the function gets to the end for some reason


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

def find_google_drive_archival(rr_number):

    target_volume = google_drive() # get the path to the story folders
    directory_list = os.listdir(target_volume)  # list contents in path
    directories = [] # to put directories in

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

    # just for safety
    return "did_not_find"

def find_archival_location(target_volume, rr_number="na"):
    # no RR number specified. Try and get it from target_volume. This doesn't work yet
    if rr_number == "na":
        rr_number = target_volume[0:5]

    root_list = os.listdir(target_volume)  # list contents in path
    root_folders = [] # to put directories in
    # go through list to sort out the directories
    for item in root_list:
        if os.path.isdir(target_volume + "/" + item): # test and see if the path leads to a directory
            root_folders.append(item)  # add directory to our list

    # get our strings to match for
    # this method will get the first match and ignore all others
    prefix_2 = rr_number.lower() + "_archival"
    prefix = rr_number.lower() + "_archival_footage"
    target = "notfound" # the check. Once this changes no more compares are made and it stores the directory we are looking for

    # Go Through all the directores and look for our strings
    for folder in root_folders:
        if target == "notfound":
            if prefix in folder.lower() or prefix_2 in folder.lower():
                target = target_volume + "/" + folder + "/"

    if target == "notfound":
        print "Could not find archival folder. Sorry"
        return "did_not_find"
    else:
        return target

    # just to cover ourselves
    return "did_not_find"


def update_volumes():
    """
    this function updates the list of valid editshare
    media drives
    :return:
    """
    print 'do something useful here'

def google_drive():
    """
    this function checks to see if the Google Drive
    is mounted on the computer. Returns path of google drive down to the Story Folders
    :return: String
    """

    # Paths to check
    google_drive_path = "/Volumes/Google_Drive"
    story_path = google_drive_path + "/_RETRO_SHARED/STORY_FOLDERS"

    if os.path.ismount(google_drive_path):
        if os.path.isdir(story_path):
            return story_path
    else:
        return "did_not_find"

    # Just to cover ourselves
    return False

def parse_asset_label(asset_label):
    """
    this function extracts the RR number
    and Asset number from a label and packs them in a list
    :return: list
    """

    # detrmine if asset label is an original (RR129) or an update (RR129.01)
    # then slice the correct characters from the asset_label string and return them.
    if asset_label[5] == "_":
        rr_number = asset_label[:5]
        asset_number = asset_label[6:10]
        pack = []
        pack.append(rr_number)
        pack.append(asset_number)
        return pack
    elif asset_label[5] == ".":
        rr_number = asset_label[:8]
        asset_number = asset_label[9:13]
        pack = []
        pack.append(rr_number)
        pack.append(asset_number)
        return pack
    else:
        # In a correct RR number the 6th character (#5 in computer speak, starting with 0) should be a '_' or '.'
        # If its not something is fucked up. Lets let the user know and exit the program

        print "So I can't find the asset number and RR number in the label"
        print "I cannot continue under these conditions"
        print "I hate you"
        exit()

def main():
    print ""

if __name__ == "__main__":
    main();