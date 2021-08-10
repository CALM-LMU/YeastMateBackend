#########################
# Imports
#########################

import os
import re
import json
import napari
import argparse
import numpy as np
from glob import glob
from skimage.io import imread, imsave
from napari.viewer import Viewer
from skimage.measure import regionprops

#########################
# Hotkeys
#########################

def set_hotkeys():
    @Viewer.bind_key('Enter', overwrite=True)
    def nxtimg(viewer):
        """Next image."""
        next_image()

def get_imglist(path):
    imglist = glob(os.path.join(path, '*.tif')) + glob(os.path.join(path, '*.tiff'))
    imglist = [x for x in imglist if not 'mask' in x]
    imglist = sorted(imglist, key=lambda f: [int(n) for n in re.findall(r"\d+", f)])
        
    return imglist


def next_image(btn=None):
    global loaded
    global counter
    global imglist

    if counter < len(imglist):
        if loaded:
            save_labels()
            counter += 1
        
        # Reset Napari view
        viewer.layers.select_all()
        viewer.layers.remove_selected()
        viewer.reset_view()

    if counter < len(imglist):
        # Load next image
        label_image()
        loaded = True

def save_labels():
    global counter
    global imglist
    global namelist

    mask = viewer.layers['single cell'].data

    things = {}

    # Add single objects to results:
    single_objects = regionprops(mask)

    rp_dict = {}
    for rp in single_objects:
        rp_dict[rp.label] = rp

    for obj in single_objects:
        bbox = [obj.bbox[1],obj.bbox[0],obj.bbox[3],obj.bbox[2]]
        bbox = [int(x) for x in bbox]

        things[str(obj.label)] = {'id': obj.label, 'box':bbox, 'class': [str(0)], 'score': [1.0], 'links': []}

    maxcounter = max(list(rp_dict.keys())) + 2

    # Add linked classes to results
    for class_idx, name in enumerate(namelist):

        data = viewer.layers[name].data

        for sample in data:
            new_mask = np.zeros_like(mask, np.uint8)
            samplelist = [list(x) for x in list(sample)]

            # Get ID of main class
            main_ids = maxcounter
            maxcounter += 1

            # Collect subobjects
            subobject_ids = []
            for n,point in enumerate(samplelist):
                sub_ids = mask[int(point[0]), int(point[1])]

                # This is hardcoded for our yeast subclassification system
                if class_idx == 0:
                    if n < 2:
                        subclass_idx = 1
                    else:
                        subclass_idx = 2
                else:
                    if n == 0:
                        subclass_idx = 1
                    else:
                        subclass_idx = 2

                fullclass_idx = "{}.{}".format(class_idx+1, subclass_idx)

                try:
                    things[str(sub_ids)]['class'].append(fullclass_idx)
                    things[str(sub_ids)]['score'].append(1.0)
                    things[str(sub_ids)]['links'].append(str(main_ids))
                except KeyError:
                    raise KeyError('All points must be within a masked object!')

                subobject_ids.append(str(sub_ids))

                new_mask[mask==sub_ids] = 1

            # Add main classes without bbox
            obj = regionprops(new_mask)[0]

            bbox = [obj.bbox[1],obj.bbox[0],obj.bbox[3],obj.bbox[2]]
            bbox = [int(x) for x in bbox]

            things[str(main_ids)] = {'id': str(main_ids), 'box': bbox, 'class': [str(class_idx+1)], 'score': [1.0], 'links': subobject_ids}

    # Generate results dictionary
    imagename = os.path.basename(imglist[counter])
    
    metadata = {}
    metadata['height'] = mask.shape[0]
    metadata['width'] = mask.shape[1]
    metadata['source'] = 'Annotation'
    metadata['detection_frame'] = None
    metadata['box_format'] = 'x1y1x2y2'

    res = {'image':imagename, 'metadata':metadata, 'detections':things}

    # Save results
    if imglist[counter].endswith('tiff'):
        imsave(imglist[counter].replace('.tiff', '_mask.tiff'), mask)

        with open(imglist[counter].replace('.tiff', '_detections.json'), 'w') as file:
            json.dump(res, file, indent=1)
    
    else:
        imsave(imglist[counter].replace('.tif', '_mask.tif'), mask)

        with open(imglist[counter].replace('.tif', '_detections.json'), 'w') as file:
            json.dump(res, file, indent=1)   

def get_imported_layers(dic, mask, score_thresholds):

    # Initialize dictionaries
    layers = {}
    rp_dict = {}

    # Get all mask objects and convert them to a dictionary with their ID keys.
    rp_objs = regionprops(mask)

    for rp in rp_objs:
        rp_dict[rp.label] = rp

    for key, thing in dic['detections'].items():

        # Split class string into main and subclass (and account for .0 edge case).
        try:
            subclass_idx = int(thing['class'][0].split('.')[1])

            if subclass_idx > 0: continue

            class_idx = int(thing['class'][0].split('.')[0])

        except IndexError:
            class_idx = int(thing['class'][0].split('.')[0])

        # No extra annotation layer for single cell (besides mask).
        if class_idx == 0: continue

        # Skip objects with score < threshold.
        if score_thresholds is not None:
            if thing['score'][0] < score_thresholds[str(class_idx)]: continue
        
        # Add class layers
        class_counter = class_idx
        while True:
            try:
                _ = layers[class_idx]
                break
            except KeyError:
                layers[class_idx] = []

                while True:
                    class_counter -= 1

                    if class_counter == 0: break

                    try:
                        _ = layers[class_counter]
                    except KeyError:
                        layers[class_counter] = []


        # Add linked objects to their layer.
        links = []
        for n,link in enumerate(thing['links']):
            obj = dic['detections'][link]

            for m, uplink in enumerate(obj['links']):
                if uplink == key:
                    subclass_idx = int(obj['class'][m+1].split('.')[1])

            # Add array for each subclass
            while True:
                try:
                    _ = links[subclass_idx - 1]
                    break
                except IndexError:
                    links.append([])

            # Get an object coordinate for path of points.
            coords = rp_dict[int(link)].coords
            point = coords[len(coords)//2]

            links[subclass_idx - 1].append(point)

        # Collapse sublists and add them to their respective layer.
        collapsed = [item for sublist in links for item in sublist]
        layers[class_idx].append(collapsed)

    return layers

def get_new_layers():
    # Default 2 (mating, budding) layers
    layers = {1: [], 2:[]}

    return layers
        
def label_image():  
    global viewer
    global counter
    global imglist
    global namelist
    global score_thresholds

    # Load image and if existing, mask and detections.json
    image = imread(imglist[counter])
        
    try:
        if imglist[counter].endswith('tiff'):
            try:
                mask = imread(imglist[counter].replace('.tiff', '_mask.tiff'))
            except:
                mask = imread(imglist[counter].replace('.tiff', '_mask.tif'))

        else:
            try:
                mask = imread(imglist[counter].replace('.tif', '_mask.tif'))
            except:
                mask = imread(imglist[counter].replace('.tif', '_mask.tiff'))

        mask = mask.astype(np.uint16)
        imported_mask = True

    except:
        mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint16)
        imported_mask = False
        print('no mask found')
    
    if imported_mask:
        try:
            if imglist[counter].endswith('tiff'):
               fileend = '.tiff'
            else:
                fileend = '.tif'
                
            with open(imglist[counter].replace(fileend, '_detections.json'), 'r') as file:
                dic = json.load(file)

            # Convert objects in detections.json to Napari layers
            layers = get_imported_layers(dic, mask, score_thresholds)  
        except:
            # Convert settings from GUI to Napari layers
            layers = get_new_layers()
            print('no json file found!')
    else:
        print('thus skipping loading json annotations')
        layers = get_new_layers()

    # Add Napari layers to viewer  

    viewer.add_image(image)    
    viewer.add_labels(mask[:,:], opacity=0.3, name='single cell', visible=True)
        
    for n in range(len(list(layers.keys()))):
        things = layers[n+1]

        if not things:
            things = None

        try:
            name = namelist[n]
        except IndexError:
            name = 'Class {}'.format(n+1)

        viewer.add_shapes(things, shape_type='path', edge_width=5, opacity=0.5, edge_color='red', face_color='red', name=name, visible=True)
            
    viewer.layers.selection.active = viewer.layers[-1]
    

if __name__ == '__main__':
    # Parse arguments from Electron frontend.
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str, help='The path to the images you want to label.')
    parser.add_argument('score_thresholds', nargs='?', default="", type=str, help='Score thresholds for the different classes.')
    args = parser.parse_args()

    path = args.path
    score_thresholds_string = args.score_thresholds

    # Set default classes.
    namelist = ['mating', 'budding']

    # Convert score thresholds from string to dictionary of floats.
    if score_thresholds_string:
        score_thresholds = {}
        score_classes = score_thresholds_string.split('C')

        for class_threshold in score_classes:
            key, value = class_threshold.split('S')

            score_thresholds[key] = float(value)
    else:
        score_thresholds = None

    # Get all tif files in folder.
    imglist = get_imglist(path)
    
    # Initialize global variables
    counter = 0
    loaded = False

    # Start napari viewer
    style = {'description_width': 'initial'}

    viewer = napari.Viewer()
    set_hotkeys()
    next_image()
    napari.run()
