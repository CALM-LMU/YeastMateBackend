from glob import glob
import requests
from skimage.io import imread, imsave

from app import huey

from alignment import *
from utils import *

import logging
logging.basicConfig(level=logging.DEBUG)

@huey.task()
def align_task(in_dir, out_dir, detection, mask, alignment, video_split, channels, file_format, dimensions, series_suffix='_series{}'):
    alignment_channel_cam1, alignment_channel_cam2, channels_cam1, channels_cam2, remove_channels = get_align_channel_vars(channels)
    tif_channels = get_align_dimension_vars(dimensions)
    
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

    if detect:
        detect_task(ARGS)   

    return 'Success'

@huey.task()
def detect_task(in_dir, out_dir, mask, cfg, weights, video_split, boxsize, channels, video):
    channel_order = get_detection_mask_channel_vars(channels)

    files_to_process = glob(os.path.join(in_dir, "*.tif"))

    for i, path in enumerate(files_to_process):
        image = imread(path)

         if video:
            image = image[-1]
        
        image = Image.fromarray(image)
        
        buffered = BytesIO()
        image.save(buffered, format="TIFF")
        image_str = base64.b64encode(buffered.getvalue()).decode('UTF-8')

        result = requests.post("http://127.0.0.1:8001/predict", json=[image_str])

        mating_boxes = []
        boxes = result['boxes']
        classes = result['classes']
        scores = result['scores']
        try:
            for n in range(len(boxes[idx])):
                if classes[idx][n] == 0 or classes[idx][n] == 1 and scores[idx][n] > 0.5:
                    mating_boxes.append(boxes[idx][n])
        except:
            print("No boxes found in {}".format(paths[idx]), flush=True)
            continue

        imgname = paths[idx].split('/')[-1]
        print('{} mating events detected in {}'.format(len(mating_boxes), imgname), flush=True)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        name = os.path.join(out_dir, os.path.splitext(path)[0].rsplit("/", 1)[-1])

        crop_img(image, mating_boxes, name)


    if mask:
        mask_task(ARGS)
    

@huey.task()
def mask_task(in_dir, out_dir, cfg, weights, channels):
    channel_order = get_detection_mask_channel_vars(channels)

    files_to_process = glob(os.path.join(in_dir, "*.tif"))

    for i, path in enumerate(files_to_process):
        image = imread(path)

         if video:
            image = image[-1]
        
        image = Image.fromarray(image)
        
        buffered = BytesIO()
        image.save(buffered, format="TIFF")
        image_str = base64.b64encode(buffered.getvalue()).decode('UTF-8')

        response = requests.post("http://127.0.0.1:8002/predict", json=[image_str])

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
        name = os.path.join(out_dir, os.path.splitext(path)[0].rsplit("/", 1)[-1])

        imsave(name+"_ATP6-NG.tif", atp)
        imsave(name+"_mtKate2.tif", kate)
        imsave(name+"_daughter.tif", daughter)

