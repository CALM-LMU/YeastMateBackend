import os
import re
import json
import argparse
import numpy as np
from glob import glob

import napari
from napari.viewer import Viewer

from PyQt5.QtWidgets import QMessageBox

from skimage.io import imread, imsave
from skimage.measure import regionprops

class YeastMateAnnotator:
    def __init__(self, path):
        self.imglist = self.get_imglist(path)

        self.namelist = ['mating', 'budding']
        self.colorlist = ['magenta', 'yellow']

        self.counter = 0
        self.loaded = False
        self.changed = False

        self.viewer = napari.Viewer()
        
        self.set_hotkeys()
        self.next_image(0)

    def save_messagebox(self):
        msg = QMessageBox()

        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Unsaved changes!")
        msg.setText("Do you want to save your changes?")

        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        reply = msg.exec_()

        if reply == 4194304:
            return 'cancel'
        elif reply == 16384:
            return 'yes'
        elif reply == 65536:
            return 'no'
        else:
            raise ValueError
    
    def set_hotkeys(self):
        @Viewer.bind_key('Enter', overwrite=True)
        def forward(viewer):
            self.next_image(1)

        @Viewer.bind_key('Left', overwrite=True)
        def backward(viewer):
            self.next_image(-1)

        @Viewer.bind_key('s', overwrite=True)
        def save(viewer):
            self.save_labels()

    @staticmethod
    def get_imglist(path):
        imglist = glob(os.path.join(path, '*.tif')) + glob(os.path.join(path, '*.tiff'))
        imglist = [x for x in imglist if not 'mask' in x]
        imglist = sorted(imglist, key=lambda f: [int(n) for n in re.findall(r"\d+", f)])
            
        return imglist

    def catch_data_change(self, event):
        self.changed = True

    def next_image(self, direction, btn=None):
        if self.counter < len(self.imglist):
            if self.loaded:
                if self.changed:
                    reply = self.save_messagebox()

                    if reply == 'cancel':
                        return
                    elif reply == 'yes':
                        self.save_labels()

                self.counter = (self.counter + direction) % len(self.imglist)
            
            # Reset Napari view
            # NB: we manually do that in label_image due to bug in napari 0.4.11
            # self.viewer.layers.select_all()
            # self.viewer.layers.remove_selected()
            # self.viewer.reset_view()

        if self.counter < len(self.imglist):
            # Load next image
            self.label_image()

            self.loaded = True
            self.changed = False

            for layer in self.viewer.layers:
                layer.events.data.connect(self.catch_data_change)

    def save_labels(self):
        mask = self.viewer.layers['single cell'].data

        if mask.max() == 0:
            return

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
        for class_idx, name in enumerate(self.namelist):

            data = self.viewer.layers[name].data

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
        imagename = os.path.basename(self.imglist[self.counter])
        
        metadata = {}
        metadata['height'] = mask.shape[0]
        metadata['width'] = mask.shape[1]
        metadata['source'] = 'Annotation'
        metadata['detection_frame'] = None
        metadata['box_format'] = 'x1y1x2y2'

        res = {'image':imagename, 'metadata':metadata, 'detections':things}

        # Save results
        if self.imglist[self.counter].endswith('tiff'):
            imsave(self.imglist[self.counter].replace('.tiff', '_mask.tif'), mask)

            with open(self.imglist[self.counter].replace('.tiff', '_detections.json'), 'w') as file:
                json.dump(res, file, indent=1)
        
        else:
            imsave(self.imglist[self.counter].replace('.tif', '_mask.tif'), mask)

            with open(self.imglist[self.counter].replace('.tif', '_detections.json'), 'w') as file:
                json.dump(res, file, indent=1)   

        self.changed = False

    def get_imported_layers(self, dic, mask):

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

    @staticmethod
    def get_new_layers():
        # Default 2 (mating, budding) layers
        layers = {1: [], 2:[]}

        return layers
            
    def label_image(self): 
        # Load image and if existing, mask and detections.json
        image = imread(self.imglist[self.counter])
            
        try:
            if self.imglist[self.counter].endswith('tiff'):
                mask = imread(self.imglist[self.counter].replace('.tiff', '_mask.tif'))

            else:
                mask = imread(self.imglist[self.counter].replace('.tif', '_mask.tif'))

            mask = mask.astype(np.uint16)
            imported_mask = True

        except:
            mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint16)
            imported_mask = False
            print('no mask found')
        
        if imported_mask:
            try:
                if self.imglist[self.counter].endswith('tiff'):
                    fileend = '.tiff'
                else:
                    fileend = '.tif'
                    
                with open(self.imglist[self.counter].replace(fileend, '_detections.json'), 'r') as file:
                    dic = json.load(file)

                # Convert objects in detections.json to Napari layers
                layers = self.get_imported_layers(dic, mask)  
            except:
                # Convert settings from GUI to Napari layers
                layers = self.get_new_layers()
                print('no json file found!')
        else:
            print('thus skipping loading json annotations')
            layers = self.get_new_layers()

        # Add Napari layers to viewer  

        # NB: napari 0.4.11 seems to crash if we remove the label layer and then add a new one
        # therefore, we add new layers first and then remove the old ones
        old_layers = list(self.viewer.layers)

        self.viewer.add_image(image)    
        self.viewer.add_labels(mask[:,:], opacity=0.3, name='single cell', visible=True)
            
        for n in range(len(list(layers.keys()))):
            things = layers[n+1]

            if not things:
                things = None

            try:
                name = self.namelist[n]
            except IndexError:
                name = 'Class {}'.format(n+1)

            self.viewer.add_shapes(things, shape_type='path', edge_width=5, opacity=0.5, edge_color=self.colorlist[n], face_color=self.colorlist[n], name=name, visible=True)
        
        # remove old layers
        for layer in old_layers:
            self.viewer.layers.remove(layer)
        
        # new layers will have received a "name [1]" label because old ones with the same name were still there
        # remove that
        for layer in self.viewer.layers:
            layer.name = layer.name.replace(' [1]', '')

        self.viewer.layers.selection.active = self.viewer.layers[-1]


if __name__ == '__main__':
    # Parse arguments from Electron frontend.
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str, help='The path to the images you want to label.')
    args = parser.parse_args()

    annotator = YeastMateAnnotator(args.path)
    napari.run()
