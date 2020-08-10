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

def crop_img(img, bboxes, name):
    for m, box in enumerate(bboxes):
        try:
            name_ = name + '_box{}'.format(m)

            x1, y1, x2, y2 = map(int, box)
            new_im = img[:,:,y1:y2,x1:x2]

            imsave(name_, new_im, imagej=True)
        except:
            continue