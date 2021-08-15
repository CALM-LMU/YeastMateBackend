import os
import sys
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from glob import glob
import pims
import cv2

from skimage.io import imread
from skimage.transform import warp
from skimage.measure import ransac
from skimage.feature import register_translation
from skimage.feature import match_descriptors, ORB, plot_matches
from skimage.transform import AffineTransform, EuclideanTransform

from tifffile import imwrite as imsave
from tifffile import memmap


def align_orb_ransac_cv2(img1, img2, plot=False):
    """
    Get Affine transformation to map img2 to img1
    OpenCV version, faster but doesn't support max_ratio for matches?
    """
    
    minsamples = 3 # just enough for 2d affine

    # normalize
    min1 = np.min(img1)
    min2 = np.min(img2)
    img1 = (img1 - min1) / (np.max(img1) - min1)
    img2 = (img2 - min2) / (np.max(img2) - min2)

    # extractor
    orb = cv2.ORB_create()
    orb.setMaxFeatures(1500)

    # detetct kp, compute descriptors
    kp1 = orb.detect((img1*255).astype(np.uint8),None)
    kp1, des1 = orb.compute((img1*255).astype(np.uint8), kp1)

    kp2 = orb.detect((img2*255).astype(np.uint8),None)
    kp2, des2 = orb.compute((img2*255).astype(np.uint8), kp2)

    # Match descriptors.
    # knnMatch not compatible with crossCheck. 
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1,des2, k=2)

    # Sort them in the order of their distance.
    #matches = sorted(matches, key = lambda x:x.distance)

    # distance ratio to second best match
    matches = [m for (m,n) in matches if m.distance/n.distance < 0.75]

    # no matches found
    if len(matches)<minsamples:
        return None

    print('Detected {}/{} keypoints, {} matches'.format(len(kp1), len(kp2), len(matches)), flush=True)

    # do RANSAC
    corr1, corr2 = np.array([kp1[m.queryIdx].pt for m in matches]), np.array([kp2[m.trainIdx].pt for m in matches])
    minsamples = 3
    model, inlier = ransac((corr1, corr2), AffineTransform, minsamples, residual_threshold=2.0, max_trials=1000)
    nInlier = sum(inlier)
    inlierRatio = sum(inlier)/len(inlier)

    print('Estimated transformation using RANSAC with {} inliers, inlier ratio {}'.format(nInlier, inlierRatio), flush=True)

    return model

def transform_planewise(img, model):
    # transform every plane of the stack
    img_t = np.zeros_like(img)

    def _plane_warp(i):
        img_t[i] += warp(img[i], model, preserve_range=True).astype(img.dtype)

    # warp planes multithreaded
    with ThreadPoolExecutor() as tpe:
        futures = [tpe.submit(_plane_warp, i) for i in range(img.shape[0])]
        [f.result() for f in futures]

    return img_t

def get_alignment_model(reader, z, fov, frame, alignment_channel_cam1, alignment_channel_cam2):
    channel_1 = []
    for zslice in range(z):
        channel_1.append(reader.get_frame_2D(t=frame, c=alignment_channel_cam1, z=zslice))
    
    channel_1 = np.max(np.asarray(channel_1), axis=0)
    
    channel_2 = []
    for zslice in range(z):
        channel_2.append(reader.get_frame_2D(t=frame, c=alignment_channel_cam2, z=zslice))
    
    channel_2 = np.max(np.asarray(channel_2), axis=0)

    model = align_orb_ransac_cv2(channel_1, channel_2)

    return model

def get_channel_offset(n_channels, remove_channels):
    channel_offset = {}

    offset = 0
    for n in range(n_channels):
        if n in remove_channels:
            offset += 1
            
        channel_offset[n] = offset

    return channel_offset

def process_single_file(path, out_dir, alignment, 
                        video_split, remove_channels=None,
                        channels_cam2=(1,3),
                        alignment_channel_cam1=0,           
                        alignment_channel_cam2=1):
    
    # create output dir, if it does not exist yet
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if not alignment:
        remove_channels = []
    
    reader = pims.Bioformats(path)

    iterax = []

    m = reader.size_series

    if not 't' in reader.sizes.keys():
        reader.sizes['t'] = 1

    if not 'z' in reader.sizes.keys():
        reader.sizes['z'] = 1

    if not 'c' in reader.sizes.keys():
         reader.sizes['c'] = 1

    t = reader.sizes['t']
    z = reader.sizes['z']
    c = reader.sizes['c']

    bundleax = ['t', 'z', 'c', 'y', 'x']
    
    reader.bundle_axes = bundleax
    reader.iter_axes = iterax

    total_c = c - len(remove_channels)

    if video_split and t == 1:
        video_split = False
    
    h,ta = os.path.split(path)
    filename = ta.rsplit('.',1)[0]

    fileending = '_series{}_frame{}.tif'

    outfile = os.path.join(out_dir, filename + fileending.format(1, 1))

    if video_split:
        imagestack = memmap(outfile, shape=(1, z, total_c, reader.sizes['y'], reader.sizes['x']), dtype=reader.pixel_type, imagej=True)
    else:
        imagestack = memmap(outfile, shape=(t, z, total_c, reader.sizes['y'], reader.sizes['x']), dtype=reader.pixel_type, imagej=True)

    for fov in range(m):
        for frame in range(t):
            if alignment:
                model = get_alignment_model(reader, z, fov, frame, alignment_channel_cam1, alignment_channel_cam2)

            channel_offset = get_channel_offset(c, remove_channels)

            for channel in range(c):
                if channel not in remove_channels:
                    new_c = channel - channel_offset[channel]

                    if alignment and channel in channels_cam2:
                        zstack = []
                        for zslice in range(z):
                            zstack.append(reader.get_frame_2D(t=frame, c=channel, z=zslice))

                        zstack = transform_planewise(np.asarray(zstack), model)

                        if video_split:
                            imagestack[0,:,new_c,:,:] = zstack
                        else:
                            imagestack[frame,:,new_c,:,:] = zstack

                    else:
                        for zslice in range(z):
                            img = reader.get_frame_2D(t=frame, c=channel, z=zslice)

                            if video_split:
                                imagestack[0,zslice,new_c,:,:] = img
                            else:
                                imagestack[frame,zslice,new_c,:,:] = img

            if video_split:
                imagestack.flush()

                if fov+1 != m or frame+1 != t:
                    if frame+1 != t:
                        outfile = os.path.join(out_dir, filename + fileending.format(fov+1, frame+2))
                    else:
                        outfile = os.path.join(out_dir, filename + fileending.format(fov+2, 1))

                    imagestack = memmap(outfile, shape=(1, z, total_c, reader.sizes['y'], reader.sizes['x']), dtype=reader.pixel_type, imagej=True)
        
        if not video_split:
            imagestack.flush()

            if fov+1 != m:
                outfile = os.path.join(out_dir, filename + fileending.format(fov+2, 1))
                imagestack = memmap(outfile, shape=(t, z, total_c, reader.sizes['y'], reader.sizes['x']), dtype=reader.pixel_type, imagej=True)

        reader.series = fov+1
        reader._change_series()
    
    del imagestack