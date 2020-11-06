import os
import json
from glob import glob

from skimage.measure import regionprops
from skimage.external.tifffile import imread as tifimread
from skimage.external.tifffile import imsave as tifimsave

from app import huey

from alignment import *
from utils import *

import logging
logging.basicConfig(level=logging.DEBUG)


@huey.task()
def start_pipeline(align, detect, path):
    return


@huey.task()
def align_task(path, detect, alignment, channels, file_format, dimensions, series_suffix='_series{}'):
    alignment_channel_cam1, alignment_channel_cam2, channels_cam1, channels_cam2, remove_channels = get_align_channel_vars(channels)
    tif_channels = get_align_dimension_vars(dimensions)

    in_dir = path
    out_dir = os.path.join(in_dir, 'aligned')
    
    # get all input files
    if file_format == '.nd2':
        files_to_process = glob(os.path.join(in_dir, "*.nd2"))
    else:
        files_to_process = glob(os.path.join(in_dir, "*.tif"))

    # align and re-save all files
    for i, path in enumerate(files_to_process):
        process_single_file({'idx': i, 'total': len(files_to_process)}, os.path.join(in_dir, path), out_dir,
                alignment=alignment, video_split=video_split,
                file_format=file_format,
                tif_channels=tif_channels, remove_channels=remove_channels, 
                series_suffix=series_suffix,
                channels_cam1=channels_cam1, channels_cam2=channels_cam2,
                alignment_channel_cam1=alignment_channel_cam1, 
                alignment_channel_cam2=alignment_channel_cam2)   


@huey.task()
def detect_task(path, zstack, graychannel, video, frame_selection, box_expansion, boxsize, ip):
    if os.path.isdir(os.path.join(path, 'aligned')):
        in_dir = os.path.join(path, 'aligned')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*.tif"))

    for i,path in enumerate(files_to_process):
        ori_image = tifimread(path)

        image = np.squeeze(ori_image)

        if video:
            if frame_selection == 'last':
                imagelist = [image[-1]]
            elif frame_selection == 'first':
                imagelist = [image[0]]
            elif frame_selection == 'all':
                imagelist = image
        else:
            imagelist = [image]

        resdict = {'image': os.path.basename(path)[-1], 'detections': []}

        for n,img in enumerate(imagelist):
            mask, meta = detect_one_image(img, zstack, graychannel, ip)

            things = regionprops(mask)

            frame = {'frame': n, 'things': []}
            for t, thing in enumerate(things):
                assert meta[t]['id'] == thing.label

                if meta[t]['isthing']:
                    obj = {'id': meta[t]['id'], 'class': meta[t]['category_id'], 'box': thing.bbox, 'score': np.round(meta[t]['score'], decimals=2)}
                    frame['things'].append(obj)

            resdict['detections'].append(frame)

        with open(path.replace('.tif', '_detections.json'), 'w') as file:
            doc = json.dump(resdict, file, indent=1)

        tifimsave(path.replace('.tif', '_mask.tif'), mask)
                

@huey.task()
def export_task(path):
    mask = tifimread(path)
    
    with open(path.replace('.tif', '_detections.json')) as file:
        metadict = json.load(file)

    

        

