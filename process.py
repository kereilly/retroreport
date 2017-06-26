# just some functions many retro scripts will use

import os.path
import parsedatetime.parsedatetime as pdt
from retrosupport.emamsidecar import Asset, FileAction, IngestAction, CustomMetadata, \
    Marker, generate_sidecar_xml, Subclip


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

        print ("So I can't find the asset number and RR number in the label")
        print ("I cannot continue under these conditions")
        print ("Your the kind of person that misses his/her first day of work!")
        exit()


def emam_metadata_format(jobs, category):

    list_assets = []
    for job in jobs:
        # Asset information
        asset = Asset()
        asset.title = job['file_name']
        asset.description = job['description']
        asset.file_name = job['file_name_ext']
        asset.file_path = "\\\\10.0.2.8\\xml_ingest"
        asset.file_action = FileAction.MOVE
        asset.ingest_action = IngestAction.CREATE_NEW_ASSET

        # Define custom metadata fields.
        custom_metadata = []
        # Mandatory fields
        metadata = CustomMetadata()  # Set metadata as CustomMetadata object
        metadata.standard_id = 'CUST_FLD_ASSET LABEL_13'    # Add the id for metadata field
        metadata.value = job['file_name']       # Add the value of the feild
        custom_metadata.append(metadata)    # append metadata to the list
        metadata = CustomMetadata()     # reset custom metadata object
        metadata.standard_id = 'CUST_FLD_ASSET NUMBER_25'
        metadata.value = job['asset_number']
        custom_metadata.append(metadata)
        metadata = CustomMetadata()
        metadata.standard_id = 'CUST_FLD_SOURCE_17'
        metadata.value = job['source']
        custom_metadata.append(metadata)
        metadata = CustomMetadata()
        metadata.standard_id = 'CUST_FLD_PROJECT ID_29'
        metadata.value = job['project_id']
        custom_metadata.append(metadata)

        # Non mandatory fields
        if job['source_id'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_SOURCE ID_18'
            metadata.value = job['source_id']
            custom_metadata.append(metadata)
        if job['description'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_DESCRIPTION_19'
            metadata.value = job['description']
            custom_metadata.append(metadata)
        if job['link'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_LINK_20'
            metadata.value = job['link']
            custom_metadata.append(metadata)
        if job['notes'] != "":
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_NOTES_32'
            metadata.value = job['notes']
            custom_metadata.append(metadata)
        #  Extract date
        dict_date = job['date']
        if dict_date['year'] != "":  # use the year as the condition if a date is present
            metadata = CustomMetadata()
            metadata.standard_id = 'CUST_FLD_DATE_5'
            date = dict_date['year']
            if dict_date['month'] != "":    # test if month is present
                date = date + "/" + dict_date['month']
            if dict_date['day'] != "":
                date = date + "/" + dict_date['month']
            metadata.value = date
            custom_metadata.append(metadata)

        # load meta data into asset
        asset.custom_metadata = custom_metadata

        # Add category
        asset.categories = category

        # load asset into list
        list_assets.append(asset)

    return list_assets


def main():
    print ("Can't be run as main()")

if __name__ == "__main__":
    main();