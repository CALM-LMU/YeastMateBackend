import json
import requests
import numpy as np
import base64
from io import BytesIO
from PIL import Image

from skimage.io import imsave

from skimage.transform import rescale
from skimage.exposure import rescale_intensity

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

def preprocess_image(image, lower_quantile, upper_quantile, pixel_size, zstack, zslice, graychannel, ref_pixel_size=110):
    if zstack:
        image = image[int(image.shape[0]*zslice)]

    if len(image.shape) > 2:    
        image = image[graychannel,:,:]

    image = image.astype(np.float32)
    lq, uq = np.percentile(image, [lower_quantile, upper_quantile])
    image = rescale_intensity(image, in_range=(lq,uq), out_range=(0,1))

    image = rescale_image(image, pixel_size, ref_pixel_size)

    return image

def detect_one_image(image, lower_quantile, upper_quantile, pixel_size, zstack, zslice, graychannel, score_thresholds, ip, ref_pixel_size=110):
    image = preprocess_image(image, lower_quantile, upper_quantile, pixel_size, zstack, zslice, graychannel, ref_pixel_size=110)
    
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

    things = result['things']
   
    mask_data = base64.b64decode(result['mask'])
    mask = Image.open(BytesIO(mask_data))
    mask = np.asarray(mask)

    things = unscale_things(things, pixel_size, ref_pixel_size)
    mask = unscale_mask(mask, pixel_size, ref_pixel_size=ref_pixel_size)

    return things, mask