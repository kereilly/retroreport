# Modules containing functions related to media for retro report

import json
import subprocess
import time
import pexpect
import sys
import re
import os
from retrosupport.process import to_trim
from retrosupport.process import formats
from retrosupport.process import resolution_type
from retrosupport.process import user_syntax


# peeks into a media file to get attributes
def getinfo(media_file):
    """
    takes a media file location and returns its
    values broken down as a dictionary
    :param media_file:
    :return: dictionary of file attributes
    """
    file_atributes = {'acodec': 'NA', 'vcodec': 'NA'}  # Dictionary to store clip information in
    # load the video information
    json_response = json.loads(ffprobe(media_file, "video"))  # get Json video data out of ffmpeg
    json_video_data = json_response["streams"]  # load the streams list    # load the json data for python
    # load the audio information
    json_response = json.loads(ffprobe(media_file, "audio"))  # get Json video data out of ffmpeg
    json_audio_data = json_response["streams"]  # load the streams list    # load the json data for python

    # Video Index            file_atributes['vcodec'] = item.get("codec_name");
    for item in json_video_data:
        file_atributes['vcodec'] = item.get("codec_name")
        file_atributes['width'] = item.get("width")
        file_atributes['height'] = item.get("height")
        file_atributes['frame_rate'] = item.get("avg_frame_rate")

    # Audio index
    for item in json_audio_data:
        file_atributes['acodec'] = item.get("codec_name")
        file_atributes['sample_rate'] = item.get("sample_rate")

    # throw in the rest of the useful information
    json_data = json_response["format"]   # load the format list
    file_atributes['duration'] = json_data["duration"]
    file_atributes['bitrate'] = json_data["bit_rate"]
    file_atributes['format_name'] = json_data["format_name"]
    file_atributes['size'] = json_data["size"]

    # calculate some stuff
    temp_string = file_atributes['frame_rate']
    string_split = temp_string.split("/")
    int1 = float(string_split[0])
    int2 = float(string_split[1])
    frame_rate = float(int1/int2)
    file_atributes['int_frame_rate'] = frame_rate
    file_atributes['frames'] = int(frame_rate * float(file_atributes['duration']))

    return file_atributes


# runs ffprobe to probe the media
def ffprobe(media, media_type="all"):

    # build command
    if media_type == "video":  # Specifically video streams
        cmd = "ffprobe -v quiet -select_streams v " \
              "-print_format json -show_format -show_streams %s" % media
    elif media_type == "audio":  # specifically audio streams
        cmd = "ffprobe -v quiet -select_streams a " \
              "-print_format json -show_format -show_streams %s" % media
    else:               # all the fucking streams
        cmd = "ffprobe -v quiet -print_format json -show_format -show_streams %s" % media

    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            )

    ffprobe_says = proc.communicate()[0]

    return ffprobe_says


# a simple progress bar
def update_progress(progress):

    bar_length = 40  # Modify this to change the length of the progress bar
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
    block = int(round(bar_length*progress))
    text = "\rPercent: [{0}] {1}% {2}".format("#"*block + "-"*(bar_length-block), progress*100, status)
    sys.stdout.write(text)
    sys.stdout.flush()


# Creates a screener file at low res
def create_screener(source, dest, verbosity=1, yadif=False):

    # Lets get some info about our file
    atributes = getinfo(source)
    # Now we have some info. Lets see if we can just copy it to the google drive
    dowhat = compress(atributes)
    if not dowhat:
        cmd = """cp %s %s""" % (source, dest)
        if verbosity >= 1:
            print ("Don't need to recompress this file. Copying as is")
    else:
        # lets get the options we need for ffmpeg
        settings = ffmpeg_settings(atributes)

        # put deinterlace into command if desired
        if yadif:
            deinterlace = "-filter:v yadif "
        else:
            deinterlace = ""

        # Determine if we need to put 'screener' in file name
        if "screener" in dest.lower():
            screener = ""
        else:
            screener = "_Screener"

    # create the command
        cmd = """ffmpeg -i %s %s %s %s%s.mp4""" % (
            source, deinterlace, settings, dest, screener)
    # to hide verbose output -hide_banner -v 10

    # launch the command
    if verbosity >= 1:
        print ("\nCreating screener at: " + dest + screener + ".mp4")

    if verbosity >= 3:
        print ("\n cmd for ffmpeg screener:\n")
        print (cmd)
    run_command(cmd, verbosity, "FFMPEG", atributes['frames'])

    if verbosity >= 1:
        print ("\nScreener Created!")


def run_command(cmd, verbosity=1, title="ffmpeg", total_frames="none"):

    if title == "bmx":
        if verbosity >= 1:
            print ("\nbmx offers no frame count output")
            print ("No progress bar")
    elif total_frames == "none":
        if verbosity >= 1:
            print ("\nWe don't have frame info on the source file")
            print ("No progress bar")
    else:
        if verbosity >= 1:
            print ("\n\nFYI the progress below bar is not accurate for now. "
                   "Despite that fact it goes to the 10th decimal place!")
            print ("It stops around 60%... or maybe not.")

    time.sleep(1)   # just so the user can read the previous output

    # Setup pexpect to launch ffmpeg
    thread = pexpect.spawn(cmd)
    cpl = thread.compile_pattern_list([pexpect.EOF, "frame= *\d+"])
    while True:
        i = thread.expect_list(cpl, timeout=None)
        if i == 0:  # EOF
            print (title + " has finished")
            break
        elif i == 1:

            frame_number = re.findall(r'\d+', thread.match.group(0))
            if str(total_frames).lower() == "none":
                sys.stdout.write(str(frame_number))
                sys.stdout.flush()
            else:
                number = (float(frame_number[0])/float(total_frames))
                update_progress(number)

    thread.close


#    proc = subprocess.Popen(cmd,
#                            shell=True,
#                            stdin=subprocess.PIPE,
#                            stdout=subprocess.PIPE,
#                            )

#    ffmpeg_says = proc.communicate()[0]
#    print ffmpeg_says

# Create a prores file


# write code here to determine if frame rate is allowed
def allowed_frame_rates(rate):
    return rate


# calculate the duration in seconds for trim
def calc_trim_duration(start, end, verbosity=1):
    # put timecode times in a list seperated by hour minute second
    list_start = str.split(start, ':')
    list_end = str.split(end, ':')

    # calculate the hour
    hour = int(list_end[0]) - int(list_start[0])
    # if hour is negative number this is an error.
    if hour < 0:
        if verbosity >= 2:
            print ("Trim function error")
            print ("Error start time must be before end time")
        return to_trim.false

    # calculate minute
    minute = int(list_end[1]) - int(list_start[1])

    # check if carry over is nessesary
    if minute < 0:
        # Check to see if we can borrow from hour. If not exit program with error
        if hour == 0:
            if verbosity >= 2:
                print ("Trim function error")
                print ("Error start time must be before end time")
            return to_trim.false

        # borrow from hour
        hour = hour - 1
        # add 60 minutes to minute
        minute = minute + 60

    # calculate seconds
    seconds = int(list_end[2]) - int(list_start[2])

    # check to see if carry over is nessesary
    if seconds < 0:
        # check to see if we can borrow from minutes
        if minute > 0:
            minute = minute - 1  # we can borrow so do it
            seconds = seconds + 60
        else:                    # we can't borrow so borrow from hours

            #  see if we can borrow from hours
            if hour < 0:
                if verbosity >= 2:
                    print ("Trim function error")
                    print ("Error start time must be before end time")
                return to_trim.false
            else:
                hour = hour - 1  # borrow from hour
                minute = minute + 59  # add to minutes except for the minute that is going to seconds
                seconds = seconds + 60

    # lets add up all the seconds now
    seconds = seconds + (minute * 60) + (hour * 3600)
    return seconds


# returns in seconds the trim time
def calc_trim_seconds(start):

    list_string = str.split(start, ":")
    seconds = int(list_string[2]) + (int(list_string[1]) * 60) + (int(list_string[0]) * 3600)

    return seconds


# Pad the string of seconds to meet required format
def trim_format(time_seconds, verbosity=1):
    if time_seconds.isdigit():  # it is all digits, see if its correct amount
        if not len(time_seconds) == 6:  # 6 digits, this checks out
            # we need to pad to get to six digits
            pad = 6 - len(time_seconds)
            if verbosity >= 3:
                print ("This time is short some digits. Adding " + str(pad) + " 0's")
                time_seconds = "0" + time_seconds
                pad = pad - 1
        # Add in the :'s in appropriate index
        time_seconds = time_seconds[0:2] + ":" + time_seconds[2:4] + ":" + time_seconds[4:]
        return time_seconds
    else:   # could be user input with :'s
        count = 0
        for char in time_seconds:
            if char == ":":
                count += 1
        if count == 2:
            index_first = time_seconds.find(":")    # find the first :
            index_last = time_seconds.rfind(":")   # find the last :
            # capture substrings
            if len(time_seconds) == (index_last + 1):   # to prevent out of index error
                seconds_string = "00"   # there are no characters after last :
            else:
                seconds_string = time_seconds[(index_last + 1):]   # add all characters after last :
            minutes_string = time_seconds[(index_first + 1):index_last]
            hours_string = time_seconds[:index_first]

            # put strings in a list for loop processing
            original_list = [seconds_string, minutes_string, hours_string]
            new_list = []   # make a new list to add too
            for stringy in original_list:
                if len(stringy) == 0:
                    stringy = "00"
                elif len(stringy) == 1:
                    stringy = "0" + stringy
                elif len(stringy) > 2:  # check for too many characters
                    if verbosity >= 1:
                        print ("More than two characters between ':'s. This is not legit for trimming operations")
                    return user_syntax.invalid

                if not stringy.isdigit():   # not an integer
                    if verbosity >= 1:
                        print ("Dude. Only put digits inbetween the ':' for trimming. Come on man!")
                    return user_syntax.invalid
                else:
                    new_list.append(stringy)  # if we got this far we just need to add it

            time_seconds = new_list[2] + ":" + new_list[1] + ":" + new_list[0]

        else:   # not enough :'s
            return user_syntax.invalid

    return time_seconds


def trim_calc(trim, media_info, verbosity=1):

    # unpack our two times
    start = str(trim[0])
    end = str(trim[1])

    if verbosity >= 3:
        print ("Trim lines before format:\nStart: " + start + "\nEnd: " + end)
    # format our times
    start = trim_format(start, verbosity)
    end = trim_format(end, verbosity)
    # check to see if format was invalid
    if start == user_syntax.invalid or end == user_syntax.invalid:
        return [user_syntax.invalid]  # return as list since this is what we deal with

    if verbosity >= 3:
        print ("After format:\nStart: " + start + "\nEnd: " + end)

    trim[0] = calc_trim_seconds(start)
    trim[1] = calc_trim_duration(start, end, verbosity)
    return trim


def trim_illegal(trim, verbosity=1):

    # unpack trim times
    start = str(trim[0])
    end = str(trim[1])

    # set our boolean, illegal, to False
    # this will make it pass the test
    is_illegal = False

    if verbosity >= 2:
        print ("Checking trim syntax")
        print ("013401 or 01:34:01 or 13401 or 1:34:1 types are acceptable.")

    temp_start = start.replace(":", "", 2)  # strip out two :'s. There should only be numbers left
    if not temp_start.isdigit():
        if verbosity >= 1:
            print ("Error with start trim time")
            print ("The only non integer characters allowed are two :'s")
        is_illegal = True  # cause this is an illegal trim time syntax

    if len(temp_start) > 6:  # are there more than 6 digits
        if not is_illegal:  # this only needs to be shown once
            print ("Error with start trim time")
        if verbosity >= 1:
            print ("Start trim time, " + str(start) + ", has more than 6 numbers")
        is_illegal = True   # cause this is an illegal trim time syntax

    if len(start) > 8:  # should only be 8 characters max
        if not is_illegal:  # this only needs to be shown once
            print ("Error with start trim time")
        if verbosity >= 1:
            print ("Start trim time, " + str(start) + ", has more than 8 characters")
        is_illegal = True   # cause this is an illegal trim time syntax

    # Check end trim time
    temp_end = end.replace(":", "", 2)
    if not temp_end.isdigit():
        if verbosity >= 1:
            print ("Error with end trim time")
            print ("The only non integer characters allowed are two :'s")
        is_illegal = True  # cause this is an illegal trim time syntax

    if len(temp_end) > 6:   # are there more than 6 digits?
        if not is_illegal:  # this only needs to be shown once
            print ("Error with start trim time")
        if verbosity >= 1:
            print ("End trim time, " + str(end) + ", has more than 6 numbers")
        is_illegal = True   # cause this is an illegal trim time syntax

    if len(end) > 8:
        if not is_illegal:  # this only needs to be shown once
            print ("Error with end trim time")
        if verbosity >= 1:
            print ("end trim time, " + str(end) + ", has more than 8 characters")
        is_illegal = True   # cause this is an illegal trim time syntax

    return is_illegal


def ffmpeg(source, dest, media_info, resolution, trim, verbosity=1, codec=formats.copy, rate=29.97):

    # put the rate variable in a string
    rate = "-r " + str(rate)

    # figure out the trimming variables
    if trim[0] == to_trim.false:  # No trimming make variables empty space
        if verbosity >= 2:
            print ("No trimming specified")
        start_trim = ""
        end_trim = ""
    elif trim_illegal(trim, verbosity):  # non legal trimming numbers
        if verbosity >= 1:
            print ("Skipping trim because of illegal trim times")
            for item in trim:
                print (str(item))
            print ("These are not valid. use 'retrodownload -h' for help menu")
        start_trim = ""
        end_trim = ""
    else:
        trim = trim_calc(trim, media_info, verbosity)
        if trim[0] == user_syntax.invalid:
            start_trim = ""
            end_trim = ""
        else:
            start_trim = "-ss " + str(trim[0])
            end_trim = "-t " + str(trim[1])

    # Set the scale variables
    width = int(media_info["width"])
    height = int(media_info["height"])
    scale = "scale=" + str(width) + ":" + str(height)

    # figure out padding offset
    if resolution == resolution_type.ntsc and codec == formats.imx50:
        pad1 = str((720 - width) / 2)
        pad2 = str((486 - height) / 2 + 26)
        pad = "pad=720:512:" + pad1 + ":" + pad2

        if verbosity >= 2:
            print ("Scale of video is " + str(width) + "x" + str(height))
            print ("IMX50 NTSC Raster is 720x512")
            print (str(720 - width) + " in width padding and " + str(512 - height) + " in height padding will be added")
            print ("Offset is: " + pad1 + ":" + pad2 + " adding 26 pixels to height for imx50 ntsc conformity")

    if resolution == resolution_type.pal and codec != formats.imx50:
        pad1 = str((720 - width) / 2)
        pad2 = str((608 - height) / 2 + 32)
        pad = "pad=720:608:" + pad1 + ":" + pad2

        if verbosity >= 2:
            print ("Scale of video is " + str(width) + "x" + str(height))
            print ("IMX50 Pal Raster is 720x608")
            print (str(720 - width) + " in width padding and " + str(608 - height) + " in height padding will be added")
            print ("Offset is: " + pad1 + ":" + pad2 + " adding 32 pixels to height for imx50 Pal conformity")

    if resolution == resolution_type.hd_high or resolution_type.hd_low:  # for now pad footage
                                                                        # with lower than 1280x720 the same
        if not width == 1920 or not height == 1080:  # if one of the demensions is off we need to fix it.
            if verbosity >= 1:
                print ("This High Def footage is not a spec raster. Padding image")
            pad1 = str((1920 - width) / 2)
            pad2 = str((1080 - height) / 2)
            hd_filters = '-vf "' + scale + ',pad=1920:1080:' + pad1 + ":" + pad2 + '" '
        else:
            hd_filters = "-s 1920:1080 "

    # now for the specific formats
    if codec == formats.imx50:  # imx50
        # Scale and codec type
        line_1 = '-vf ' + '"' + scale + ':interl=0:in_color_matrix=bt709:out_color_matrix=bt601,' + pad + \
                 ',tinterlace=4:flags=vlpf" -c:v mpeg2video -pix_fmt yuv422p'

        # codec options, audio and flags
        line_2 = ' -b:v 50M -minrate 50M -maxrate 50M -bufsize 2M -rc_init_occupancy 2M -intra -flags ' \
                 '+ildct+low_delay -intra_vlc 1 -non_linear_quant 1 -ps 1 -qmin 1 -qmax 3 -top 1 -dc 10 ' \
                 '-c:a pcm_s24le -ar 48000 -d10_channelcount 4 -f mxf_d10'

        options = line_1 + line_2

    elif codec == formats.copy:  # just re-wrapping or trimming
        options = "-c:v copy -c:a copy"
        # erase rate option
        rate = ""

    elif codec == formats.xdcam422:
        line_1 = hd_filters + "-vcodec mpeg2video -profile:v 0 -level:v 2 -b:v 50000k " \
                              "-maxrate 50000k -bufsize 3835k -minrate 50000k "
        line_2 = "-flags ilme -top 1 -acodec pcm_s24le -ar 48000 -pix_fmt yuv422p"
        options = line_1 + line_2

    # Create the command with all our options
    cmd = """ffmpeg %s -i %s %s %s %s %s""" % (
            start_trim, source, end_trim, rate, options, dest)

    if verbosity >= 3:
        print ("\n\n\n ******FFMPEG COMMAND******\n")
        print (cmd)

    # call ffmpeg
    run_command(cmd, verbosity, "FFMPEG", media_info['frames'])

    # More post processing if we are working with HD footage
    if resolution == resolution_type.hd_high or resolution_type.hd_low:
        if os.path.isfile(dest):
            size_transcoded = os.path.getsize(dest)
            size_original = os.path.getsize(source)
            if verbosity >= 2:
                print ("Size of original file: " + str(size_original))
                print ("Size of transcoded file: " + str(size_transcoded))
            if size_transcoded > 300:
                source = dest
                index = source.rfind(".")  # to index where the extention starts
                dest = source[:index] + "_BMX.mxf"
                cmd = "bmxtranswrap -p -o %s %s" % (dest, source)
                # Call BMX
                if verbosity >= 1:
                    print ("Running bmxtranswrap to re-wrap clips in mxf format for fast Avid import")
                run_command(cmd, verbosity, "bmx")
                if os.path.isfile(dest):
                    dest_info = getinfo(dest)
                    source_info = getinfo(source)
                    if verbosity >= 3:
                        print ("\nSource frame count: " + str(dest_info['frames']))
                        print ("BMX output frame count: " + str(source_info['frames']))

                    if dest_info['frames'] == source_info['frames']:
                        if verbosity >= 1:
                            print ("Removing ffmpeg's file at " + source)
                        os.remove(source)
                    else:
                        if verbosity >= 1:
                            print ("Well bmx re-wrapped a clip but somthing looks wrong. Keeping both files")
                        if verbosity >= 2:
                            print ("A " + str((dest_info['frames'] - source_info['frames'])) +
                                   " frame difference between the two")
                            print ("ffmpeg: " + source)
                            print ("-check this one: bmx " + dest)
                else:
                    if verbosity >= 1:
                        print ("Can't find BMX's output file")
            else:
                if verbosity >= 1:
                    print ("Found ffmpegs output but somthing looks wrong. Not re wraping")
        else:
            if verbosity >= 1:
                print ("Something went wrong with ffmpeg transcoding")
                print ("Life sucks sometimes.")
    return dest


#   Create the ffmpeg command line string for screeners
def ffmpeg_settings(attributes):
    """
    creates the ffmpeg command as a string
    based on factors in the original file (its scale)
    :param attributes:
    :return: command as string
    """
    scale = calcscale(attributes)
    command = (
        '-vcodec libx264 -preset medium -b:v 180k -r 15 -b:a 64k'
        ' -ar 48000 %s -pix_fmt yuv420p -profile:v high -strict -2'
            ) % scale
    return command


#   Determines the scale of the screener file
#   Based on its original raster and a compression ratio
def calcscale(attributes):
    """
    determines the scale of the screener file
    formats it as string for ffmpeg command
    :param attributes:
    :return:
    """
    print ("\n\tCalcScale:")
    # ffprobe did not find dementions. Go with generic size
    if str(attributes["width"]) == "None":
        print ('\nWarning!: Can\'t find dimentions of media!')
        print ('Using default target size, aspect ratio might not be correct')
        time.sleep(1)
        new_width = 474
        new_height = 268
        print ("Screener width: " + str(new_width))
        print ("Screener height: " + str(new_height))
    else:
        # find what the dimentsions should be
        divide_by = float(attributes["width"]) / 474  # get the number to divde with based on a target of 474
        if divide_by < 1.1:     # don't need to change the scale since its so close
            print ("Don't need to resize this one\n")
            new_width = roundscale(attributes["width"])
            new_height = roundscale(attributes["height"])
        else:
            new_width = roundscale(float(attributes["width"]) / divide_by)
            new_height = roundscale(float(attributes["height"]) / divide_by)
            print ("Divided by: " + str(divide_by))

        print ("Original width: " + str(attributes["width"]))
        print ("Screener width: " + str(new_width))
        print ("Original heigt: " + str(attributes["height"]))
        print ("Screener height: " + str(new_height))

    scale = '-vf "scale=' + str(new_width) + 'x' + str(new_height) + '"'

    return scale


#   Determine's wether or not the file needs to be recompressed
def compress(attributes):
    """
    determines weather or not file downloaded needs
    to be compressed
    :param attributes:
    :return: Boolean
    """

    # if its not h264 for video and aac for audio we don't want it
    if attributes["vcodec"] != "h264":
        print ("Media not in h264 video format")
        return True
    elif attributes["acodec"] != "aac":
        print ('audio not in "aac" format')
        return True

    # lets figure out the size, we'll use abitrate and vbitrate for this
    bitrate = attributes["bitrate"]
    # if the bitrate is small enough lets leave it all be
    if bitrate < 250000:
        return False
    else:
        print ("Bit rate of file too high. Re-compressing")
        return True


#   Rounds the raster so ffmpeg doesn't trip on an uneven integer
def roundscale(scale):
    """
    rounds the scale of video screener
    to make it an even integer
    :param scale:
    :return: scale as integer
    """
    int_scale = int(scale)    # Convert to integer
    if not int_scale % 2 == 0:     # check to see if its even, add one if not
        int_scale = int_scale + 1

    return int_scale


def main():
    print ("can't be run as main()")


if __name__ == "__main__":
    main()
