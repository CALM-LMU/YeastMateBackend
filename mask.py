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

from biodetectron.eval import MaskPredictor

def inference_on_folder(self, folder, channel_order=[0,1,2], zproject=True, norm=True, graytrain=False):
        pathlist = glob(os.path.join(folder, '*.jpg')) + \
                  glob(os.path.join(folder, '*.tif')) + \
                  glob(os.path.join(folder, '*.png'))

        panlist = []
        for path in pathlist:
            image = imread(path)

            image = np.max(image, axis=0)
            if channel_order != [0,1,2]:
                stack = []
                for ch in channel_order:
                    stack.append(image[ch])
                image = np.asarray(image)

            pan = self.detect_one_image(image, zproject=zproject, norm=norm, graytrain=graytrain)
            panlist.append(pan)

        return pathlist, panlist


def preprocess_img(self, image, norm=False, zproject=True, graytrain=False):
    if norm:
        image = image.astype(np.float32)
        image = rescale_intensity(image)
    
    height, width = image.shape[1:3]
    image = torch.as_tensor(image.astype("float32"))
    image = {"image": image, "height": height, "width": width}

    return image