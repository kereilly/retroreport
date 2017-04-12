# just some functions many retro scripts will use

import sys
import os.path
import parsedatetime.parsedatetime as pdt


# Classes that need to work accross modules
class volume_result(object):
    not_found = 0
    found = 1
    invalid_asset_label = 2

    def __init__(self, archival_location):
        self.archival_location = archival_location

class user_syntax(object):
    invalid = 0
    valid = 1
class download_result(object):
    download_failed = 0
    download_success = 1
    invalid_asset_label = 2
    file_not_found = 3
    multiple_file_found = 4

class resolution_type(object):
    ntsc = 2
    pal = 3
    hd_low = 4
    hd_high = 5

class formats(object):
    prores_proxy = 2
    prores_lt = 3
    prores_hq = 4
    proros_444 = 5
    h264 = 6
    copy = 7
    imx50 = 8
    xdcam422 = 9

class frame_rates(object):
    f23_94 = 23.94
    f24 = 24
    f25 = 25
    f29_97 = 29.97
    f30 = 30
    f60 = 60


class to_trim(object):
    false = 0
    true = 1

def open_file(path, mode = "r"):

    if os.path.isfile(path):
        processed_file = open(path, mode)
        return processed_file
    else:
        return volume_result.not_found

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
        print "Your the kind of person that misses his/her first day of work!"
        exit()

## takes a string returns a python date
def datetimeFromString(s):

    c = pdt.Calendar()
    result, what = c.parse(s)

    dt = None

    # what was returned (see http://code-bear.com/code/parsedatetime/docs/)
    # 0 = failed to parse
    # 1 = date (with current time, as a struct_time)
    # 2 = time (with current date, as a struct_time)
    # 3 = datetime
    if what in (1,2):
        # result is struct_time
        dt = datetime.datetime(*result[:6])
    elif what == 3:
        # result is a datetime
        dt = result

    if dt is None:
        # Failed to parse
        raise ValueError, ("Don't understand date '"+s+"'")

    return dt

def main():
    print "Can't be run as main()"

if __name__ == "__main__":
    main();