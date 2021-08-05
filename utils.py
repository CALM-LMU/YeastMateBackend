import os
import copy
import numpy as np

from skimage.io import imsave as skimsave
from tifffile import imwrite as tifimsave

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

def parse_export_classes(array):
    crop_classes = []

    tags = {}
    for cls in array:
        if cls['Crop'] == 'True':
            crop_classes.append(int(cls['Class ID']))

        val_tag = cls['Tag']

        val_tag = val_tag.replace(" ", "_")
        val_tag = val_tag.lower()

        tags[int(cls['Class ID'])] = val_tag

    return crop_classes, tags

def get_class_indices(key, dic):
    class_indices = {}
    for n,link in enumerate(dic[key]['links']):
        obj = dic[link]

        for m, uplink in enumerate(obj['links']):
            if uplink == key:
                subclass_idx = int(obj['class'][m+1].split('.')[1])

        class_indices[link] = subclass_idx

    return class_indices

def enlarge_box(box, boxsize, height, width):
    x1, y1, x2, y2 = map(int, box)
    boxsize = boxsize//2

    centerx = (x1 + x2) // 2
    centery = (y1 + y2) // 2

    centerx = min(max(0+boxsize, centerx), width-boxsize)
    centery = min(max(0+boxsize, centery), height-boxsize)

    return centerx-boxsize, centery-boxsize, centerx+boxsize, centery+boxsize

def scale_box(box, boxscale, height, width):
    x1, y1, x2, y2 = map(int, box)

    boxsize_x = x2 - x1
    boxsize_y = y2 - y1

    boxsize_x *= boxscale
    boxsize_y *= boxscale

    centerx = (x1 + x2) // 2
    centery = (y1 + y2) // 2

    centerx = min(max(0+boxsize_x, centerx), width-boxsize_x)
    centery = min(max(0+boxsize_y, centery), height-boxsize_y)

    return centerx-boxsize_x, centery-boxsize_y, centerx+boxsize_x, centery+boxsize_y

def negate_boolean(b):
    return not b


def crop_img(img, box, out_dir, filename, tag, index, cls_indices, meta, box_expansion, boxsize, boxscale_switch, boxscale, mask, tiff=False):
    basename, extension = os.path.splitext(filename)
    name_ = basename + '_' + tag + '_' + str(index)

    if tiff:
        suffix = '.tiff'
    else:
        suffix = '.tif'

    if mask:
        name_ = name_ + '_mask'

    if box_expansion:
        x1, y1, x2, y2 = enlarge_box(box, boxsize, meta['height'], meta['width'])
    elif boxscale_switch:
        x1, y1, x2, y2 = scale_box(box, boxscale, meta['height'], meta['width'])
    else:
        x1, y1, x2, y2 = map(int, box)
    
    if len(img.shape) == 4:
        new_im = img[:,:,y1:y2,x1:x2]
    elif len(img.shape) == 3:
        new_im = img[:,y1:y2,x1:x2]
    elif len(img.shape) == 2:
        new_im = img[y1:y2,x1:x2]
    elif len(img.shape) == 5:
        new_im = img[:,:,:,y1:y2,x1:x2]

    else:
        print('Not supported image shape!')
        return

    if mask:
        new_mask = np.zeros_like(new_im)

        for idx, cls_idx in cls_indices.items():
            new_mask[new_im == int(idx)] = cls_idx
        
        new_im = new_mask.astype(np.uint8)

    tifimsave(os.path.join(out_dir, name_ + suffix), new_im, imagej=negate_boolean(mask))
