import json
import requests
import numpy as np
import base64
from io import BytesIO
from PIL import Image

from skimage.io import imsave

from skimage.transform import rescale
from skimage.exposure import rescale_intensity
from skimage.color import rgb2gray

import logging

def get_scale_factor(pixel_size, ref_pixel_size=110):
    return pixel_size/ref_pixel_size

def rescale_image(image, pixel_size, ref_pixel_size=110):
    scale_factor = get_scale_factor(pixel_size, ref_pixel_size)

    if scale_factor != 1.0:
        image = rescale(image, scale_factor, preserve_range=True)

    return image

def unscale_mask(image, pixel_size, ref_pixel_size=110):
    scale_factor = get_scale_factor(pixel_size, ref_pixel_size)
    scale_factor = 1/scale_factor

    if scale_factor != 1.0:
        image = rescale(image, scale_factor, preserve_range=True, anti_aliasing=False, order=0)

    return image

def unscale_things(things, pixel_size, ref_pixel_size=110):
    scale_factor = get_scale_factor(pixel_size, ref_pixel_size)
    scale_factor = 1/scale_factor

    if scale_factor != 1.0:
        for n, thing in enumerate(things):
           things[n]['box'] = [x*scale_factor for x in thing['box']]

    return things

def preprocess_image(image, lower_quantile, upper_quantile, pixel_size, ref_pixel_size=110):
    image = image.astype(np.float32)
    lq, uq = np.percentile(image, [lower_quantile, upper_quantile])
    image = rescale_intensity(image, in_range=(lq,uq), out_range=(0,1))

    image = rescale_image(image, pixel_size, ref_pixel_size)

    return image

def get_detection_frame(image, zstack, zslice, multichannel, graychannel, video, frame_selection):
    framedict = {'t':"", "z":"", "c":""}

    image = np.squeeze(image)

    try:
        if video:
            if frame_selection == 'last':
                framedict['t'] = str(image.shape[0])
                image = image[-1]
            elif frame_selection == 'first':
                framedict['t'] = "0"
                image = image[0]

        if zstack:
            framedict['z'] = int(image.shape[0]*zslice)
            image = image[framedict['z']]

        if multichannel: 
            framedict['c'] = graychannel  
            image = image[graychannel,:,:]
        else:
            if len(image.shape) == 3 and image.shape[-1] == 3:
                image = rgb2gray(image)
    except IndexError:
        raise IndexError('Image dimensions too small for selected video, zstack and channel settings!')

    if len(image.shape) > 2:
        raise IndexError('Image dimensions too big for selected video, zstack and channel settings! Image musts consist only of time, z, channel and XY dimensions.')

    frame = image.copy()

    return frame, framedict

def detect_one_image(image, score_thresholds, ip):    
    image = image.astype(np.float32)
    image = Image.fromarray(image, mode='F')
    
    imagebytes = BytesIO()
    image.save(imagebytes, format="TIFF")
    imagebytes.seek(0)

    score_bytes = json.dumps(score_thresholds).encode('utf-8')

    filedict = {"image": ('image.tiff', imagebytes, 'image/tiff') , \
                    "annotations": ('score_thresholds.json', score_bytes)
                }

    result = requests.post("http://{}/predict".format(ip), files=filedict).json()

    detections = result['detections']
   
    mask_data = base64.b64decode(result['mask'])
    mask = Image.open(BytesIO(mask_data))
    mask = np.asarray(mask)

    things = unscale_things(things, pixel_size, ref_pixel_size)
    mask = unscale_mask(mask, pixel_size, ref_pixel_size=ref_pixel_size)

    return detections, mask