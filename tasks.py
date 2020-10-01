import os
import json
import requests
from glob import glob

from skimage.exposure import rescale_intensity
from skimage.io import imread, imsave

import base64
from io import BytesIO
from PIL import Image

from app import huey

from alignment import *
from utils import *

import logging
logging.basicConfig(level=logging.DEBUG)

@huey.task()
def start_pipeline(align, detect, path):
    return

@huey.task()
def align_task(path, detect, alignment, video_split, channels, file_format, dimensions, series_suffix='_series{}'):
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
def detect_task(path, zstack, video_split, graychannel, video, fiji, boxsize, ip="127.0.0.1:5000"):
    if os.path.isdir(os.path.join(path, 'aligned')):
        in_dir = os.path.join(path, 'aligned')
    else:
        in_dir = path

    out_dir = os.path.join(path, 'cropped')

    files_to_process = glob(os.path.join(in_dir, "*.tif"))

    for i, path in enumerate(files_to_process):
        ori_image = imread(path)

        image = np.squeeze(ori_image)

        if video:
            image = image[-1]

        if zstack:
            image = np.max(image, axis=0)

        if len(image.shape) > 2:    
            image = image[:,:, 0]

        image = np.expand_dims(image, axis=-1)
        image = np.repeat(image, 3, axis=-1)

        image = rescale_intensity(image, out_range=(0,255))
        image = image.astype(np.uint8)
     
        image = Image.fromarray(image)
        
        imagebytes = BytesIO()
        image.save(imagebytes, format="PNG")
        imagebytes.seek(0)
        imagedict = {"image": ('image.png', imagebytes, 'image/png')}

        result = requests.post("http://{}/predict".format(ip), files=imagedict).json()

        mating_boxes = []
        boxes = result['boxes']
        classes = result['classes']
        scores = result['scores']

        try:
            for n, box in enumerate(boxes):
                if classes[n] == 1:
                    mating_boxes.append(box)
        except:
            print("No boxes found in {}".format(paths[idx]), flush=True)
            continue

        imgname = os.path.basename(path)
        print('{} mating events detected in {}'.format(len(mating_boxes), imgname), flush=True)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        name = os.path.join(out_dir, imgname)

        crop_img(ori_image, mating_boxes, name, fiji, boxsize)

@huey.task()
def mask_task(path, zstack, channels):
    return
    channel_order = get_detection_mask_channel_vars(channels)

    if os.path.isdir(os.path.join(path, 'cropped')):
        in_dir = os.path.join(path, 'cropped')
    else:
        in_dir = path

    out_dir = os.path.join(path, 'masked')

    files_to_process = glob(os.path.join(in_dir, "*.tif"))

    for i, path in enumerate(files_to_process):
        image = imread(path)

        if video:
            image = image[-1]

        if zstack:
            image = np.max(image, axis=0)
        if len(image.shape) < 3:
            image = np.expand_dims(image, axis=-1)
            image = np.repeat(image, 3, axis=-1)
        elif image.shape[-1] == 1:
            image = np.repeat(image, 3, axis=-1)

        if channel_order != [0,1,2]:
            stack = []
            for ch in channel_order:
                stack.append(image[ch])
            image = np.asarray(stack)
        
        image = Image.fromarray(image)
        
        imagebytes = BytesIO()
        image.save(imagebytes, format="PNG")
        imagebytes.seek(0)
        imagedict = {"image": ('image.png', imagebytes, 'image/png')}

        response = requests.post("http://127.0.0.1:5000/predict_mask", files=imagedict)

        mating_boxes = []
        seg = result['pans'][0]
        meta = result['pans'][1]
        
        atp = np.zeros_like(seg)
        kate = np.zeros_like(seg)
        daughter = np.zeros_like(seg)

        spent_cats = []
        extra_cats = []
        for item in meta[:3]:
            if item["category_id"] not in spent_cats:
                if item["category_id"] == 1:
                    atp[seg==item["id"]] = 1
                elif item["category_id"] == 2:
                    kate[seg==item["id"]] = 1
                elif item["category_id"] == 3:
                    daughter[seg==item["id"]] = 1
                spent_cats.append(item["category_id"])
            else:
                extra_cats.append(item)

        if len(extra_cats) == 1:
            for n, item in enumerate(meta[:3]):
                if n not in spent_cats:
                    if item["category_id"] == 1:
                        atp[seg==item["id"]] = 1
                    elif item["category_id"] == 2:
                        kate[seg==item["id"]] = 1
                    elif item["category_id"] == 3:
                        daughter[seg==item["id"]] = 1
        elif len(extra_cats) == 0:
            pass
        else:
            print('Cell identities could not be determined!', flush=True)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        name = os.path.join(out_dir, path.rsplit("/", 1)[-1])

        imsave(name+"_ATP6-NG.tif", atp)
        imsave(name+"_mtKate2.tif", kate)
        imsave(name+"_daughter.tif", daughter)
