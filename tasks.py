import os
import json
import numpy as np
from glob import glob

from skimage.transform import rescale
from skimage.measure import regionprops
from skimage.feature import greycomatrix, greycoprops

from tifffile import memmap as tifimread
from tifffile import imwrite as tifimsave

from app import huey

from alignment import process_single_file
from utils import get_align_channel_vars, get_align_dimension_vars, crop_img, parse_export_classes
from detection import detect_one_image
from config import reference_pixel_size
           
import logging
logging.basicConfig(level=logging.DEBUG)


@huey.task()
def start_pipeline():
    return


@huey.task()
def preprocessing_task(path, alignment, channels, file_format, dimensions, video_split, series_suffix='_series{}'):
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
def detect_task(path, include_tag, exclude_tag, zstack, graychannel, lower_quantile, upper_quantile, pixel_size, video, frame_selection, ip):
    if os.path.isdir(os.path.join(path, 'aligned')):
        in_dir = os.path.join(path, 'aligned')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*.tif"))
    files_to_process = [x for x in files_to_process if include_tag in x]

    if exclude_tag != '':
        files_to_process = [x for x in files_to_process if exclude_tag not in x]

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
            frame_selection = 'null'

        resdict = {'image': os.path.basename(path), 'metadata': {}, 'detections': []}

        maskarray = []
        for n,img in enumerate(imagelist):
            things, mask = detect_one_image(img, lower_quantile, upper_quantile, pixel_size, zstack, graychannel, ip, ref_pixel_size=reference_pixel_size)

            resdict['detections'] = things

            maskarray.append(mask)

        maskarray = np.squeeze(np.asarray(maskarray))
        
        resdict['metadata']['height'] = imagelist[0].shape[0]
        resdict['metadata']['width'] = imagelist[0].shape[1]
        resdict['metadata']['detection_frame'] = frame_selection
        resdict['metadata']['source'] = 'Detection'
        resdict['metadata']['bbox_format'] = 'x1y1x2y2'

        tifimsave(path.replace('.tif', '_mask.tif'), maskarray)
        with open(path.replace('.tif', '_detections.json'), 'w') as file:
            doc = json.dump(resdict, file, indent=1)
                

@huey.task()
def export_task(path, crop, classes, video, video_split, score_threshold, box_expansion, boxsize):
    if os.path.isdir(os.path.join(path, 'aligned')):
        in_dir = os.path.join(path, 'aligned')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*_detections.json"))

    crop_classes, mask_classes, tags = parse_export_classes(classes)

    if crop:
        if len(crop_classes) == 0 and len(mask_classes) == 0:
            return
    
        out_dir = os.path.join(path, 'crops')
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

    for filepath in files_to_process:
        try:
            with open(filepath) as file:
                metadict = json.load(file)

            if len(crop_classes) > 0:
                image = tifimread(filepath.replace('_detections.json', '.tif'))

            if len(mask_classes) > 0:
                mask = tifimread(filepath.replace('_detections.json', '_mask.tif'))
        
        except:
            print('Input files corrupted!')
            continue

        filename = os.path.basename(filepath.replace('_detections.json', '.tif'))

        if crop:
            for framekey, frame in enumerate(metadict['detections']):
                for thing in frame:
                    if float(thing['score']) < score_threshold:
                        continue

                    box = thing['box']

                    if video and metadict['detection_frame'] == 'all':
                        if thing['class'] in crop_classes:
                            crop_img(image[int(framekey)], box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=False)
                        if thing['class'] in mask_classes:
                            crop_img(mask[int(framekey)], box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=True)
                    else:
                        if thing['class'] in crop_classes:
                            crop_img(image, box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=False)
                        if thing['class'] in mask_classes:
                            crop_img(mask, box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=True)
