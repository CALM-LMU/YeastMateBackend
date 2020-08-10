import os
import sys
import argparse
import warnings
import numpy as np
from glob import glob

import PIL
PIL.PILLOW_VERSION = '7.9'

import torch
from skimage import img_as_float
from skimage.io import imsave as imsave_prev
from skimage.exposure import rescale_intensity
from skimage.external.tifffile import imread, imsave

from biodetectron.eval import BboxPredictor
from biodetectron.utils import box2csv

def zcxy_inference_on_folder(self, folder, boxsize, video=False, channel_order=[0,1,2], saving=True, norm=False, check_iou=True, graytrain=False):
    pathlist = glob(os.path.join(folder, '*.jpg')) + \
               glob(os.path.join(folder, '*.tif')) + \
               glob(os.path.join(folder, '*.png'))

    print('Predicting on {} images'.format(len(pathlist)), flush=True)

    for path in pathlist:
        image = imread(path)

        if video:
            image = image[-1]
            boxes, classes, scores = self.detect_one_image(image, boxsize, channel_order=channel_order, norm=norm, check_iou=check_iou)

            for idx in range(image.shape[0]):
                newpath = os.path.splitext(path)[0] + '_frame{}'.format(idx) + os.path.splitext(path)[1]


        else:
            boxes, classes, scores = self.detect_one_image(image, boxsize, norm=norm, check_iou=check_iou)


        if saving:
            box2csv(boxes, classes, scores, os.path.splitext(path)[0] + '_predict.csv')

    return newpathlist, imglist, boxlist, classlist, scorelist


def detect_one_image(self, image, boxsize, channel_order=[0,1,2], norm=False, check_iou=True):
        image, h, w = self.preprocess_img(image, channel_order=channel_order, norm=norm)

        with torch.no_grad():
            instances = self.model([image])[0]["instances"]

        boxes = list(instances.pred_boxes)
        boxes = [tuple(box.cpu().numpy()) for box in boxes]

        new_boxes = []
        for box in boxes:
            x1, y1, x2, y2 = box

            centerx = (x1 + x2) / 2
            centery = (y1 + y2) / 2

            centerx = min(max(0+boxsize, centerx), w-boxsize)
            centery = min(max(0+boxsize, centery), h-boxsize)

            new_boxes.append([centerx-boxsize, centery-boxsize, centerx+boxsize, centery+boxsize])
    
        scores = list(instances.scores)
        scores = [score.cpu().numpy() for score in scores]

        classes = list(instances.pred_classes)
        classes = [cls.cpu().numpy() for cls in classes]

        if check_iou:
            new_boxes, classes, scores = self.check_iou(new_boxes, scores, classes)

        return new_boxes, classes, scores


def preprocess_img(self, image, channel_order=[0,1,2], norm=False, augment=False, graytrain=False, zproject=True):
    image = np.max(image, axis=0)
    if channel_order != [0,1,2]:
        stack = []
        for ch in channel_order:
            stack.append(image[ch])
     
        image = np.asarray(stack)

    height, width = image.shape[1:3]

    image = torch.as_tensor(image.astype("float32"))
    image = {"image": image, "height": height, "width": width}

    return image, height, width


def crop_img(img, bboxes, name):
    for m, box in enumerate(bboxes):
        try:
            name_ = name + '_box{}'.format(m)

            x1, y1, x2, y2 = map(int, box)
            new_im = img[:,:,y1:y2,x1:x2]

            imsave(name_, new_im, imagej=True)
        except:
            continue
