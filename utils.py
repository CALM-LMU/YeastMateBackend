import os
import numpy as np
from skimage.io import imsave

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

    centerx = (x1 + x2) / 2
    centery = (y1 + y2) / 2

    centerx = min(max(0+boxsize, centerx), w-boxsize)
    centery = min(max(0+boxsize, centery), h-boxsize)

    return centery-boxsize, centerx-boxsize, centery+boxsize, centerx+boxsize

def crop_img(img, bboxes, name, fiji, boxsize):
    for m, box in enumerate(bboxes):
        filename, extension = os.path.splitext(name)
        name_ = filename + '_box{}'.format(m) + extension
      
        if len(img.shape) == 4:
            if img.shape[1] < img.shape[-1]:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[-2], img.shape[-1])
                new_im = img[:,:,y1:y2,x1:x2]
            else:
                y1, x1, y2, x2 = enlarge_box(box, boxsize, img.shape[1], img.shape[2])
                new_im = img[:,y1:y2,x1:x2,:]
                if fiji:
                    new_im = np.transpose(new_im, (0,3,1,2))
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
                if fiji:
                    new_im = np.transpose(new_im, (0,1,4,2,3))
        else:
            print('Not supported image shape!')
            continue

        imsave(name_, new_im, imagej=True)