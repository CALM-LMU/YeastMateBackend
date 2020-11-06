import os
import json
import requests
import numpy as np

import base64
from io import BytesIO
from PIL import Image

from skimage.exposure import rescale_intensity
from skimage.io import imsave as skimsave
from skimage.external.tifffile import imsave as tifimsave

def get_align_channel_vars(channels):
    channels_cam1 = []
    channels_cam2 = []
    remove_channels = []

    for idx, channel in enumerate(channels):
        if channel['Camera'] == 1:
            channels_cam1.append(idx)

            if channel['DIC'] == 'True':
                alignment_channel_cam1 = idx

        elif channel['Camera'] == 2:
            channels_cam2.append(idx)

            if channel['DIC'] == 'True':
                alignment_channel_cam2 = idx

        if channel['Delete'] != 'Keep':
            remove_channels.append(idx)
    
    return alignment_channel_cam1, alignment_channel_cam2, channels_cam1, channels_cam2, remove_channels

def get_align_dimension_vars(dimensions):
    minus_counter = 0
    tif_channels = {}

    ## Test this!

    for idx, dim in enumerate(dimensions):
        if dim['status'] == 'Existing':
            tif_channels[dim['Dimension']] = idx - minus_counter
        else:
            minus_counter += 1
            tif_channels[dim['Dimension']] = None

    return tif_channels

def get_detection_mask_channel_vars(channels):
    channel_order = [0, 1, 2]
    for idx, ch in enumerate(channels):
        if ch['Type'] == 'DIC':
            channel_order[0] = idx
        elif ch['Type'] == 'Red':
            channel_order[1] = idx
        elif ch['Type'] == 'Green':
            channel_order[2] = idx

    return channel_order

def enlarge_box(box, boxsize, height, width):
    y1, x1, y2, x2 = map(int, box)
    boxsize = boxsize//2

    centerx = (x1 + x2) // 2
    centery = (y1 + y2) // 2

    centerx = min(max(0+boxsize, centerx), width-boxsize)
    centery = min(max(0+boxsize, centery), height-boxsize)

    return centery-boxsize, centerx-boxsize, centery+boxsize, centerx+boxsize


def detect_one_image(image, zstack, graychannel, ip):
    if zstack:
        image = np.max(image, axis=0)

    if len(image.shape) > 2:    
        image = image[graychannel,:,:]

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

    mask = np.asarray(result['mask'])
    meta = result['meta']

    return mask, meta


def crop_img(img, bboxes, name, boxsize, video_split):
    for m, box in enumerate(bboxes):
        filename, extension = os.path.splitext(name)
        name_ = filename + '_box{}'.format(m)
      
        if len(img.shape) == 4:
            if img.shape[1] < img.shape[-1]:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[-2], img.shape[-1])
                new_im = img[:,:,y1:y2,x1:x2]
            else:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[1], img.shape[2])
                new_im = img[:,y1:y2,x1:x2,:]
        elif len(img.shape) == 3:
            if img.shape[0] < img.shape[-1]:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[-2], img.shape[-1])
                new_im = img[:,y1:y2,x1:x2]
            else:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[0], img.shape[1])
                new_im = img[y1:y2,x1:x2,:]
        elif len(img.shape) == 2:
            y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[0], img.shape[1])
            new_im = img[y1:y2,x1:x2]
        elif len(img.shape) == 5:
            if img.shape[2] < img.shape[-1]:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[-2], img.shape[-1])
                new_im = img[:,:,:,y1:y2,x1:x2]
            else:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[-3], img.shape[-2])
                new_im = img[:,:,y1:y2,x1:x2,:]
        else:
            print('Not supported image shape!')
            continue

        if video_split:
            # get filename before suffix
            foldername, filename = os.path.split(name_)

            if not os.path.exists(os.path.join(foldername, filename + '_single_frames')):
                os.makedirs(os.path.join(foldername, filename + '_single_frames'))

            for fileidx in range(new_im.shape[0]):
                # construct new filename
                outfile = os.path.join(foldername, filename + '_single_frames', filename + '_slice{}'.format(fileidx) + '.tif')
                            
                # save as ImageJ-compatible tiff stack
                tifimsave(outfile, new_im[fileidx], imagej=True)
        
        tifimsave(name_ + '.tif', new_im, imagej=True)