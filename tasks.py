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

            frame_detection = frame_selection
        else:
            imagelist = [image]
            frame_detection = 'null'

        resdict = {'image': os.path.basename(path)[-1], 'detection_frame': frame_detection, 'detections': []}

        maskarray = []
        for n,img in enumerate(imagelist):
            mask, meta = detect_one_image(img, zstack, graychannel, ip)

            things = regionprops(mask)

            frame = {'frame': n, 'things': []}
            for t, thing in enumerate(things):
                assert meta[t]['id'] == thing.label

                if box_expansion:
                    y1, x1, y2, x2 = enlarge_box(thing.bbox, boxsize, mask.shape[0], mask.shape[1])
                else:
                    y1, x1, y2, x2 = map(int, thing.bbox)

                if meta[t]['isthing']:
                    obj = {'id': meta[t]['id'], 'class': meta[t]['category_id'], 'box': [x1, y1, x2, y2], 'score': np.round(meta[t]['score'], decimals=2)}
                    frame['things'].append(obj)

            resdict['detections'].append(frame)
            maskarray.append(mask)

        with open(path.replace('.tif', '_detections.json'), 'w') as file:
            doc = json.dump(resdict, file, indent=1)

        maskarray = np.asarray(mask)
        maskarray = np.squeeze(maskarray)

        tifimsave(path.replace('.tif', '_mask.tif'), mask)
                

@huey.task()
def export_task(path, crop, classes, video_split, score_threshold):
    if os.path.isdir(os.path.join(path, 'aligned')):
        in_dir = os.path.join(path, 'aligned')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*_detections.json"))

    crop_classes, mask_classes, tags = parse_export_classes(classes)

    if len(crop_classes) == 0 and len(mask_classes) == 0:
        return
    
    out_dir = os.path.join(path, 'crops')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    for filepath in files_to_process:
        with open(filepath) as file:
            metadict = json.load(file)

        if len(crop_classes) != 0:
            image = tifimread(filepath.replace('_detections.json', '.tif'))

        if len(mask_classes) != 0:
            mask = tifimread(filepath.replace('_detections.json', '_mask.tif'))

        filename = os.path.basename(filepath.replace('_detections.json', '.tif'))

        for frame in metadict['detections']:
            for index, thing in enumerate(frame['things']):
                if float(thing['score']) < score_threshold:
                    continue

                box = thing['box']

                if metadict['detection_frame'] == 'all':
                    if thing['class'] in crop_classes:
                        crop_img(image[int(framekey)], box, out_dir, filename, tags[thing['class']], index, video_split=video_split, mask=False)
                    if thing['class'] in mask_classes:
                        crop_img(mask[int(framekey)], box, out_dir, filename, tags[thing['class']], index, video_split=video_split, mask=True)
                else:
                    if thing['class'] in crop_classes:
                        crop_img(image, box, out_dir, filename, tags[thing['class']], index, video_split=video_split, mask=False)
                    if thing['class'] in mask_classes:
                        crop_img(mask, box, out_dir, filename, tags[thing['class']], index, video_split=video_split, mask=True)


            if metadict['detection_frame'] != 'all':
                break

        

    

        

