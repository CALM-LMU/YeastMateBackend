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

from alignment import *
from utils import *
           
import logging
logging.basicConfig(level=logging.DEBUG)


@huey.task()
def start_pipeline(alignment, detection, export, path):
    return


@huey.task()
def preprocessing_task(path, doDetection, doExport, alignment, channels, file_format, dimensions, video_split, series_suffix='_series{}'):
    import time
    time.sleep(30)

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
def detect_task(path, doExport, include_tag, exclude_tag, zstack, graychannel, scale_factor, video, frame_selection, ip):
    if os.path.isdir(os.path.join(path, 'aligned')):
        in_dir = os.path.join(path, 'aligned')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*.tif"))
    files_to_process = [x for x in files_to_process if include_tag in x]

    if exclude_tag != '':
        files_to_process = [x for x in files_to_process if exclude_tag not in x]

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

        resdict = {'image': os.path.basename(path)[-1], 'meta': {}, 'detection_frame': frame_detection, 'detections': []}

        maskarray = []
        for n,img in enumerate(imagelist):
            res = detect_one_image(img, zstack, graychannel, scale_factor, ip)

            resdict['detections'].append(res['things'])
            mask = np.asarray(res["mask"]).reshape(res['height'], res['width'], res['channel'])

            if scale_factor != 1:
                mask = rescale(mask, (1/scale_factor, 1/scale_factor, 1))

            maskarray.append(mask)

        maskarray = np.squeeze(np.asarray(maskarray))
        
        resdict['meta']['height'] = res['height']
        resdict['meta']['width'] = res['width']

        tifimsave(path.replace('.tif', '_mask.tif'), maskarray)
        with open(path.replace('.tif', '_detections.json'), 'w') as file:
            doc = json.dump(resdict, file, indent=1)
                

@huey.task()
def export_task(path, measure, crop, classes, video, video_split, score_threshold, box_expansion, boxsize):
    if os.path.isdir(os.path.join(path, 'aligned')):
        in_dir = os.path.join(path, 'aligned')
    else:
        in_dir = path

    files_to_process = glob(os.path.join(in_dir, "*_detections.json"))

    crop_classes, mask_classes, tags = parse_export_classes(classes)

    if crop:
        if not measure and len(crop_classes) == 0 and len(mask_classes) == 0:
            return
    
        out_dir = os.path.join(path, 'crops')
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

    for filepath in files_to_process:
        try:
            with open(filepath) as file:
                metadict = json.load(file)

            if len(crop_classes) > 0:
                image = tifimread(filepath.replace('_detections.json', '.tif'))

            if len(mask_classes) > 0:
                mask = tifimread(filepath.replace('_detections.json', '_mask.tif'))
        
        except:
            print('Input files corrupted!')
            continue

        filename = os.path.basename(filepath.replace('_detections.json', '.tif'))

        if measure:   
            neongreen = tifimread(filepath.replace('TransCon_detections.json', '488nm.tif'))
            if mask[:,:,-1].max() < 1:
                continue
            
            scores = []
            for th in metadict['detections']:
                if th["class"] == 3:
                    scores.append(th["score"])
            
            matings = regionprops(mask[:,:,-1])
            
            for n,mating in enumerate(matings):
                if scores[n] < 1:
                    continue 
                    
                mothercrop = mask[:,:,1][mating.bbox[0]:mating.bbox[2],mating.bbox[1]:mating.bbox[3]]
                matingcrop = mask[:,:,-1][mating.bbox[0]:mating.bbox[2],mating.bbox[1]:mating.bbox[3]]
                daughtercrop = mask[:,:,2][mating.bbox[0]:mating.bbox[2],mating.bbox[1]:mating.bbox[3]]
                
                mothers = regionprops(mothercrop)
                daughters = regionprops(daughtercrop)
            
                if len(mothers) < 2:
                    continue
                
                newmothers = []
                for mot in mothers:
                    if mot.area > 100:
                        newmothers.append(mot)
                        
                mothers = newmothers
                
                if len(daughters) > 1:
                    dscores = []          
                    for daughter in daughters:
                        for r in metadict['detections']:
                            if r['id'] == daughter.label:
                                dscores.append(r['score'])
                                
                    daughteridx = np.argmax(dscores)
                    daughters = [daughters[daughteridx]]
                    
                while len(mothers) > 3:
                    overlap = []
                    for mot in mothers:
                        overlap.append(np.sum(matingcrop[mothercrop == mot.label]))
                        
                    overlapidx = np.argmin(overlap)
                    del mothers[overlapidx]
                                
                if len(daughters) == 1 and len(mothers) > 2:
                    overlap = []
                    for mot in mothers:
                        overlap.append(np.sum(daughtercrop[mothercrop == mot.label]))
                        
                    overlapidx = np.argmax(overlap)
                    del mothers[overlapidx]
                    
                if len(mothers) > 2:                 
                    continue
                
                xses = []
                yses = []
                bses = []
                cses = []
                dses = []
                means = []
                maxes = []
                for th in mothers:
                    motherbox = neongreen[mating.bbox[0]:mating.bbox[2],mating.bbox[1]:mating.bbox[3]][th.bbox[0]:th.bbox[2],th.bbox[1]:th.bbox[3]]
                    motherbox[mothercrop[th.bbox[0]:th.bbox[2],th.bbox[1]:th.bbox[3]] != th.label] = 0
                    
                    glcm = greycomatrix(motherbox, distances=[5], angles=[0], levels=neongreen.max()+1, symmetric=True, normed=True)
                    xs = greycoprops(glcm, 'dissimilarity')
                    ys = greycoprops(glcm, 'correlation')
                    bs = greycoprops(glcm, 'contrast')
                    cs = greycoprops(glcm, 'homogeneity')
                    ds = greycoprops(glcm, 'ASM')
                    
                    xses.append(xs)
                    yses.append(ys)
                    bses.append(bs)
                    cses.append(cs)
                    dses.append(ds)
                    means.append(np.mean(neongreen[mating.bbox[0]:mating.bbox[2],mating.bbox[1]:mating.bbox[3]][mothercrop == th.label]))
                    maxes.append(np.max(neongreen[mating.bbox[0]:mating.bbox[2],mating.bbox[1]:mating.bbox[3]][mothercrop == th.label]))
                
                maxs = max(maxes)
                for entry in metadict['detections']:
                    if entry['id'] == mating.label:
                        assert entry['class'] == 3
                        entry['mean_distance'] = float(np.abs(means[0]-means[1]))
                        entry['mean_distance_normed'] = float(np.abs(means[0]/maxs-means[1]/maxs))
                        entry['dissimilarity'] = float(np.abs(xses[0]-xses[1]))
                        entry['correlation'] = float(np.abs(yses[0]-yses[1]))
                        entry['contrast'] = float(np.abs(bses[0]-bses[1]))
                        entry['homogeneity'] = float(np.abs(cses[0]-cses[1]))
                        entry['ASM'] = float(np.abs(dses[0]-dses[1]))

            with open(filepath, 'w') as file:
                print(filepath)
                doc = json.dump(metadict, file, indent=1)
                print(metadict)
        
        if crop:
            for framekey, frame in enumerate(metadict['detections']):
                for thing in frame:
                    if float(thing['score']) < score_threshold:
                        continue

                    box = thing['box']

                    if video and metadict['detection_frame'] == 'all':
                        if thing['class'] in crop_classes:
                            crop_img(image[int(framekey)], box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=False)
                        if thing['class'] in mask_classes:
                            crop_img(mask[int(framekey)], box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=True)
                    else:
                        if thing['class'] in crop_classes:
                            crop_img(image, box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=False)
                        if thing['class'] in mask_classes:
                            crop_img(mask, box, out_dir, filename, tags[thing['class']], thing['id'], metadict['meta'], box_expansion, boxsize, video_split=video_split, mask=True)
