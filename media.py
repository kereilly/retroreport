## Modules containing functions related to media for retro report

import json
import subprocess
import time
import pexpect
import sys
import re

#peeks into a media file to get attributes
def getinfo(media_file):
    """
    takes a media file location and returns its
    values broken down as a dictionary
    :param media_file:
    :return: dictionary of file attributes
    """
    file_atributes = {} # Dictionary to store clip information in
    # load the video information
    jsonResponse = json.loads(ffprobe(media_file, "video"))  # get Json video data out of ffmpeg
    jsonVideoData = jsonResponse["streams"]  # load the streams list    # load the json data for python
    # load the audio information
    jsonResponse = json.loads(ffprobe(media_file, "audio"))  # get Json video data out of ffmpeg
    jsonAudioData = jsonResponse["streams"]  # load the streams list    # load the json data for python

      # Video Index            file_atributes['vcodec'] = item.get("codec_name");
    for item in jsonVideoData:
        file_atributes['vcodec'] = item.get("codec_name");
        file_atributes['width'] = item.get("width");
        file_atributes['height'] = item.get("height");
        file_atributes['frame_rate'] = item.get("avg_frame_rate");

         # Audio index
    for item in jsonAudioData:
        file_atributes['acodec'] = item.get("codec_name");
        file_atributes['sample_rate'] = item.get("sample_rate");

    # throw in the rest of the useful information
    jsonData = jsonResponse["format"]   # load the format list
    file_atributes['duration'] = jsonData["duration"];
    file_atributes['bitrate'] = jsonData["bit_rate"];
    file_atributes['format_name'] = jsonData["format_name"];
    file_atributes['size'] = jsonData["size"];

    # calculate some stuff
    string = file_atributes['frame_rate']
    string_split = string.split("/")
    int1 = float(string_split[0])
    int2 = float(string_split[1])
    frame_rate = float(int1/int2)
    file_atributes['int_frame_rate'] = frame_rate
    file_atributes['frames'] = int(frame_rate * float(file_atributes['duration']))


    return file_atributes

# runns ffprobe to probe the media
def ffprobe(media, type = "all"):

    # build command
    if type == "video":  # Specifically video streams
        cmd = "ffprobe -v quiet -select_streams v " \
              "-print_format json -show_format -show_streams %s" % media
    elif type == "audio":  # specifically audio streams
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
    #print "ffprobe:"
    #print ffprobe_says
    return ffprobe_says

# a simple progress bar
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


# Creates a screener file at low res
def create_screener(source, dest, yadif = False):

    # Lets get some info about our file
    atributes = getinfo(source)
    # Now we have some info. Lets see if we can just copy it to the google drive
    dowhat = compress(atributes)
    if not dowhat:
        cmd = """cp %s %s""" % (source, dest)
        print "Don't need to recompress this file. Copying as is"

    #if dowhat ==:
    #    cmd == """ffmpeg -i % -codec copy %""" % (source, dest)
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
    print "\ncreating screener at: " + dest + screener + ".mp4"
    print "\n\nFYI the progress below bar is not accurate for now. Despite that fact it goes to the 10th decimal place!"
    print "It stops around 60%... or maybe not."
    time.sleep(1)   # just so the user can read the previous output
    thread = pexpect.spawn(cmd)
   # print "started %s" % cmd
   # we need the number of frames in this video for progress bar
    total_frames = atributes['frames']
    cpl = thread.compile_pattern_list([pexpect.EOF, "frame= *\d+"])
    while True:
        i = thread.expect_list(cpl, timeout=None)
        if i == 0: # EOF
            print "ffmpeg has finished"
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
    print "\nScreener Created!"

#   Create the ffmpeg command line string
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
            ) % (scale)
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
    print "\n        CalcScale:"
    # ffprobe did not find dementions. Go with generic size
    if str(attributes["width"]) == "None":
        print '\nWarning!: Can\'t find dimentions of media!'
        print 'Using default target size, aspect ratio might not be correct'
        time.sleep(1)
        new_width = 474
        new_height = 268
        print "Screener width: " + str(new_width)
        print "Screener height: " + str(new_height)
    else:
    # find what the dimentsions should be
        divide_by = float(attributes["width"]) / 474 # get the number to divde with based on a target of 474
        if divide_by < 1.1:     # don't need to chagne the scale since its so close
            print "Don't need to resize this one\n"
            new_width = roundscale(attributes["width"])
            new_height = roundscale(attributes["height"])
        else:
            new_width = roundscale(float(attributes["width"]) / divide_by)
            new_height = roundscale(float(attributes["height"]) / divide_by)
            print "Divided by: " + str(divide_by)

        print "Original width: " + str(attributes["width"])
        print "Screener width: " + str(new_width)
        print "Original heigt: " + str(attributes["height"])
        print "Screener height: " + str(new_height)
        print "\n"

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
        print "Media not in h264 video format"
        return True
    elif attributes["acodec"] != "aac":
        print 'audio not in "aac" format'
        return True

    # lets figure out the size, we'll use abitrate and vbitrate for this
    bitrate = attributes["bitrate"]
    # if the bitrate is small enough lets leave it all be
    if bitrate < 250000:
        return False
    else:
        print "Bit rate of file too high. Re-compressing"
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
    if not int_scale%2==0:     # check to see if its even, add one if not
        int_scale = int_scale + 1

    return int_scale

def main():
    print "can't be run as main()"

if __name__ == "__main__":
    main();