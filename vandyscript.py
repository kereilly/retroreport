#!/usr/bin/env python
## Retro Screener & Media for Edit conversion for Vandy Clips
## uses ffmbc for avid media
## uses ffmpeg for conversion of screeners
## Version 1.4
## 12/04/15

import sys
import os
import re
import subprocess
import time


google_drive_path = "/Volumes/Google_Drive/_RETRO_SHARED/Story_Folders/"
google_drive_root = "/Volumes/Google_Drive/"
screener_location = "STORYFOLDER/RRXXX_ARCHIVAL/RRXXX_SCREENERS_ARCHIVAL/"
Edit_Material_Dir_Name = "_Converted_for_Edit"


# to pick out the asset number in the directory path
def asset(string):
    #search the string for the pattern 'A' followed by some digits
    numbers = re.findall(r'A\d+', string)
    return numbers[0]   # it may find more than one match. I will
                        #take the first one. Don't need the rest, if any

# to pick out RR number in directory path
def rr_number(string):

    # search the string for the pattern 'RR' followed by some digits
    numbers = re.findall(r'RR\d+', string)
    return numbers[0]   # it may find more than one match. I will
                        #take the first one. Don't need the rest, if any

# probe all the directories in the path specified for the user looking
#for the keywords in both directories and files inside them
def scan(path, screener):
    add_to_list = False
    files = False
    dirlist = []        #initilize list for 'ripped to mpeg' directories
    final_list = []     #final list of directories to work with
    filtered_list = []  
    
    topdown = os.walk(path) #go through directory user specified
    
    for root, dirs, files, in topdown:
        for dirname in dirs:
             # search for the ripped to mpeg folder
            if ("ripped" in dirname.lower() or "mpeg" in dirname.lower()
                or "mpg" in dirname.lower()):
                # well one of the keywords were found so lets do something
                # add to list of directories with the keyword in its
                # full path
                dirlist.append(os.path.join(root, dirname)) 

    # process each entry that was found,
    #check for apropriate files and "converted for edit directory"
    for item in dirlist:
        file_list = os.listdir(item)
        
        # check for appropriate files mpeg or mpg
        for files in file_list:
            if files[0] != "." and ".mpg" in files.lower() or ".mpeg" in files.lower():
                filtered_list.append(files) # now a list with no hidden files
                files = True    #their is an appropriate file to process
                                #Proceed to next step
                
            #the next step, check for "converted for edit" directory on level up
        if files:
            add_to_list = True  # add directory to final list
                
            # now check to see if their already is a "converted for edit" folder"
            # skip if screener option selected
        if screener == False:
            index = item.rfind('/') # find the last '/' in directory path
            higher_dir = item[0:index] # move up one directory
            up_one_dir_list = os.listdir(higher_dir) # populate list one directory up
            # perform the check
            for more_items in up_one_dir_list:
                if "converted" in more_items.lower() or "edit" in more_items.lower():
                    add_to_list = False  # don't add to list afterall footage has been processed.
                    
         # well if it passed all the checks add it to the lest           
        if add_to_list:
            final_list.append(item)
            add_to_list = False # reset the list bool
            
    return final_list

# convert media
def ffmpeg(dirlist, screener, yadif):
    global screener_location
    output = ""
    file_location = ""
    rr = 0
    
    for item in dirlist:    # step through each directory in list
        #get list of files in directory 
        files = os.listdir(item)
        print "Files in directory:"
        print files
        print ""
        #get the rr number associated with these clips
        rr = rr_number(item)
        print "Clips appear to be associated with story " + rr
        print ""
        time.sleep(1)
        
        # find the story folder to go along with this rrnumber
        process_screeners = False # seed as false so screeners are skipped if screener folder not found
        story_folders = os.listdir(google_drive_path)
        for folder in story_folders:
            if rr == folder[0:len(rr)]:
                target_story = folder
                process_screeners = True    # to ensure screeners will only be made if story folder found
                screener_path = google_drive_path # set the path to the normal location of story folders for the sreeners
        if process_screeners == False:      # It didn't find the story folder. Check in the root of google drive
            story_folders = os.listdir(google_drive_root)
            for folder in story_folders:
                if rr == folder[0:len(rr)]:
                    # we have a hit but might be a file
                    check = google_drive_root + folder  # Put the potential path string together
                    if os.path.isdir(check):
                        potential_folder = os.listdir(check)
                        for stuffs in potential_folder:
                            if "CAMERA_REPORTS" in stuffs:
                                # we found our story folder
                                target_story = folder
                                process_screeners = True    # to ensure screeners will only be made if story folder found
                                screener_path = google_drive_root   # set the path for the root of the google drive for the screeners
              
        print "sorting through files, only working on mpg's"
        time.sleep(1)
        for clip in files:  # step through each file
            
            # make sure we only work with mpeg files
            if ".mpg" in clip.lower() or ".mpeg" in clip.lower() and clip[0] != ".":
                print "Working on: " + clip + " in"
                print item
                time.sleep(1)

                # check to see if file name has RR number and asset number
                # if not add them to file.
                output = clip               # start with clip name
                if not rr_number(item) in clip:
                    # no rr number so go ahead and add it at the begining
                    message = "No RR number in clip name: " + output + " adding RR number: " + rr
                    print message
                    output = rr_number(item) + "_" + clip
                    time.sleep(1)
                
                retro_number = rr_number(item)  # grab RR number
                asset_number = asset(item)  # grab asset number
                
                if not asset(item) in clip:
                    # no asset number so add to the end before the .extention
 
                    message = "No asset number or a mismatch in clip name: " + output + " adding asset number: " + asset_number 
                    print message
                    output = output.replace('.' , '_' + asset_number + '.') # add asset number to output file name
                    time.sleep(1)

                #store file location for ffmpeg
                file_location = item + "/" + clip
               
                #prepare output variable
                index = output.rfind('.')   #find location of extention
                output = output[0:index]    #strip off the extention

                # process media for edit unless in screener only mode
                if not screener:
                    # make directory and prep output variable for ffmpeg for the converted for edit media
                    index = item.rfind('/') # find the last '/' in directory path
                    converted_edit_path = item[0:index] + "/" + retro_number + "_" + asset_number + "_" + "Converted_for_Edit" # move up one directory and add Converted for edit dir
                    if not os.path.exists(converted_edit_path): # if directory already exists don't create it
                        print "Creating Directory: " + converted_edit_path
                        print ""
                        os.mkdir(converted_edit_path) # create the converted for edit directory
                    converted_edit_path += "/" # prep directory path for ffmpeg
                    edit_output = converted_edit_path + output + '.mxf' # create output path and add mov extention

                    # Create the command
                    if yadif:
                        cmd = """ffmbc -i %s -r 29.97 -target imx50 -vf yadif=0:1 %s""" % (
                            file_location, edit_output)
                    else:
                        print "Creating avid media without deinterlace"
                        cmd = """ffmbc -i %s -r 29.97 -target imx50 %s""" % (
                            file_location, edit_output)

                    # launch the command
                    print "createing converted to edit media at: " + edit_output
                    proc = subprocess.Popen(cmd,
                                        shell=True,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        )
    
                    ffmbc_says = proc.communicate()[0]
                    print ffmbc_says
  

             # Now proccess the screener unless path was not found (check with boolean)
                if process_screeners:

                     # build path string for screeners
                    local_screener_location = screener_location.replace("STORYFOLDER", target_story) # reset local_screener_location variable, set story folder
                    local_screener_location = local_screener_location.replace("RRXXX", rr)  # set rr number
                    local_screener_location = screener_path + local_screener_location                               
                    Screener_output = local_screener_location + output + '_Screener.mp4'            #add mp4 extention for screeners and add location to save screeners
                    
                    
                    # create the command
                    if yadif:
                        cmd = """ffmpeg -i %s -vf "scale='iw/2':-1" -filter:v yadif -c:v libx264 -preset veryslow -b:v 250k -b:a 64k -strict -2 %s""" % (
                                file_location, Screener_output)
                    else:
                        print "Creating Screener without deinterlace"
                        cmd = """ffmpeg -i %s -vf "scale='iw/2':-1" -c:v libx264 -preset veryslow -b:v 250k -b:a 64k -strict -2 %s""" % (
                                file_location, Screener_output)
                    # launch the command
                    print "creating screener at: " + Screener_output
                    proc = subprocess.Popen(cmd,
                                            shell=True,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            )
    
                    ffmpeg_says = proc.communicate()[0]
                    print ffmpeg_says
  
                            

def main():

    screener = False    # screener only mode. set to false
    yadif = True        # deinterlace media. Default is on
    
    # make sure correct arguments were given
    if len(sys.argv) == 1:
        print "No options given to rrmediaconverter. You must at least enter a directory to process"
        exit()
    elif len(sys.argv) >= 4:
        print "Too many options!"
        print "You have confused rrmediaconverter!"
        exit() 
    elif os.path.isdir(sys.argv[1]) == False:
        print sys.argv[1] + "is not a valid directory"
        exit()
    # check for optional screener argument
    if len(sys.argv) == 3:
        if sys.argv[2] != "screener" and sys.argv[2] != "yadif":
            print "What is '" + sys.argv[2] + "'. That's not a Valid option man!"
            print "Correct syntax is:"
            print "'rrmediaconverter /directory_to_process'"
            print "or"
            print "'rrmediaconverter /directory_to_Process screener/yadif' for just screeners or to disable yadif"
            exit()
        if sys.argv[2] == "screener":
            screener = True
        if sys.argv[2] == "yadif":
            yadif = False
        
    print "Processing Media in Path "
    print sys.argv[1]

    #scan the user provided directory and store the directories to process
    dir_list = scan(sys.argv[1], screener)

    if len(dir_list) == 0:
        print "No valid directories/media to process"
        exit()
    
    print "Found valid media in following "
    print len(dir_list)
    print  " locations:"
    time.sleep(1)
    print dir_list
    time.sleep(2)
    ffmpeg(dir_list, screener, yadif)

if __name__ == "__main__":
    main();
