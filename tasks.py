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
from utils import *
from detection import *
           
import logging
logging.basicConfig(level=logging.DEBUG)


@huey.task()
def start_pipeline(path, alignment, detection, export):
    return


@huey.task()
def preprocessing_task(path, detection, export, alignment, channels, video_split):
    alignment_channel_cam1, alignment_channel_cam2, channels_cam1, channels_cam2, remove_channels = get_align_channel_vars(channels)

    in_dir = path
    out_dir = os.path.join(in_dir, 'yeastmate-preprocessed')
    
    files_to_process = glob(os.path.join(in_dir, "*"))
    files_to_process = [path for path in files_to_process if os.path.isfile(path)]

    # align and re-save all files
    for path in files_to_process:
        try:
            process_single_file(path, out_dir,
                    alignment=alignment, 
                    video_split=video_split,
                    remove_channels=remove_channels, 
                    channels_cam2=channels_cam2,
                    alignment_channel_cam1=alignment_channel_cam1, 
                    alignment_channel_cam2=alignment_channel_cam2
                )   
        except Exception as e:
            print(e)
            continue


@huey.task()
def detect_task(path, export, include_tag, exclude_tag, zstack, zslice, multichannel, graychannel, lower_quantile, upper_quantile, score_thresholds, pixel_size, ref_pixel_size, video, frame_selection, ip, port):
    if os.path.isdir(os.path.join(path, 'yeastmate-preprocessed')):
        in_dir = os.path.join(path, 'yeastmate-preprocessed')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*.tif")) + glob(os.path.join(in_dir, "*.tiff"))
    files_to_process = [x for x in files_to_process if include_tag in x]

    if exclude_tag != '':
        files_to_process = [x for x in files_to_process if exclude_tag not in x]

    for i,path in enumerate(files_to_process):
        image = tifimread(path)

        image, framedict = get_detection_frame(image, zstack, zslice, multichannel, graychannel, video, frame_selection)
        original_shape = image.shape

        image = preprocess_image(image, lower_quantile, upper_quantile, pixel_size, ref_pixel_size)
        
        try:
            detections, mask = detect_one_image(image, score_thresholds, ip, port)
        except:
            print('Image corrupted/unfit for detection, skipping image!')
            continue

        detections, mask = unscale_results(detections, mask, original_shape, pixel_size, ref_pixel_size)

        resdict = {'image': os.path.basename(path), 'metadata': {}, 'detections': detections}
                
        resdict['metadata']['height'] = image.shape[0]
        resdict['metadata']['width'] = image.shape[1]
        resdict['metadata']['detection_frame'] = framedict
        resdict['metadata']['source'] = 'Detection'
        resdict['metadata']['bbox_format'] = 'x1y1x2y2'

        if path.endswith('tiff'):
            tifimsave(path.replace('.tiff', '_mask.tiff'), mask)
            with open(path.replace('.tiff', '_detections.json'), 'w') as file:
                doc = json.dump(resdict, file, indent=1)
        else:
            tifimsave(path.replace('.tif', '_mask.tif'), mask)
            with open(path.replace('.tif', '_detections.json'), 'w') as file:
                doc = json.dump(resdict, file, indent=1)
                

@huey.task()
def export_task(path, classes, box_expansion, boxsize, boxscale_switch, boxscale):
    
    crop_classes, tags = parse_export_classes(classes)

    if len(crop_classes) == 0:
        return

    if os.path.isdir(os.path.join(path, 'yeastmate-preprocessed')):
        in_dir = os.path.join(path, 'yeastmate-preprocessed')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*_mask.tif")) + glob(os.path.join(in_dir, "*_mask.tiff"))

    out_dir = os.path.join(in_dir, 'crops')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    for filepath in files_to_process:
        try:
            if len(crop_classes) > 0:
                if path.endswith('tiff'):
                    tiffmask = True
                    try:
                        image = tifimread(filepath.replace('_mask.tiff', '.tiff'))
                        tiffimg = True
                    except:
                        image = tifimread(filepath.replace('_mask.tiff', '.tif'))
                        tiffimg = False
                else:
                    tiffmask = False
                    try:
                        image = tifimread(filepath.replace('_mask.tif', '.tif'))
                        tiffimg = False
                    except:
                        image = tifimread(filepath.replace('_mask.tif', '.tiff'))
                        tiffimg = True

            mask = tifimread(filepath)
  
            if path.endswith('tiff'):
                with open(filepath.replace('_mask.tiff', '_detections.json')) as file:
                    dic = json.load(file)
            else:
                with open(filepath.replace('_mask.tif', '_detections.json')) as file:
                    dic = json.load(file)
            
        except:
            print('Input file corrupted!')
            continue

        filename = os.path.basename(filepath)

        for key,thing in dic['detections'].items():
            try:
                subclass_idx = int(thing['class'][0].split('.')[1])

                if subclass_idx > 0: continue

                class_idx = int(thing['class'][0].split('.')[0])

            except IndexError:
                class_idx = int(thing['class'][0].split('.')[0])

            if class_idx == 0: continue

            box = thing['box']

            cls_indices = get_class_indices(key, dic['detections'])

            if class_idx in crop_classes:
                crop_img(image, box, out_dir, filename, tags[class_idx], thing['id'], cls_indices, dic['metadata'], box_expansion, boxsize, boxscale_switch, boxscale, mask=False, tiff=tiffimg)
                crop_img(mask, box, out_dir, filename, tags[class_idx], thing['id'], cls_indices, dic['metadata'], box_expansion, boxsize, boxscale_switch, boxscale, mask=True, tiff=tiffmask)
