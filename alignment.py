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


def transform_planewise(img, model, axes):
    # transform every plane of the stack
    if 'z' in axes:
        img_t = np.zeros_like(img)

        def _plane_warp(i):
            img_t[i] += warp(img[i], model, preserve_range=True).astype(img.dtype)

        # warp planes multithreaded
        with ThreadPoolExecutor() as tpe:
            futures = [tpe.submit(_plane_warp, i) for i in range(img.shape[0])]
            [f.result() for f in futures]

    else:
        img_t = warp(img, model, preserve_range=True).astype(img.dtype)
    
    return img_t


def process_single_file(path, out_dir, alignment, video_split, remove_channels=None, series_suffix='_series{}',
                        channels_cam1=(0,2), channels_cam2=(1,3),
                        alignment_channel_cam1=0,           
                        alignment_channel_cam2=1):
    
    # create output dir, if it does not exist yet
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if not alignment:
        remove_channels = []
    
    try:
        reader = pims.ND2_Reader(path)
    except:
        reader = pims.Bioformats(path)

    reader.sizes['t'] = 10
    del reader.sizes['m']

    iterax = ''
    if 'm' in reader.sizes.keys():
        iterax += 'm'
        m = reader.sizes['m']
    else:
        m = 1

    if 't' in reader.sizes.keys():
        iterax += 't'
        t = reader.sizes['t']
    else:
        t = 1

    bundleax = 'c'
    if 'z' in reader.sizes.keys():
        bundleax += 'z'
        z = reader.sizes['z']
    else:
        z = 1

    bundleax += 'yx'
    
    c = reader.sizes['c'] - len(remove_channels)

    reader.bundle_axes = bundleax
    reader.iter_axes = iterax
    
    # go through single images
    h,ta = os.path.split(path)
    filename = ta.rsplit('.',1)[0]

    if not video_split:
        imagestack = memmap(os.path.join(out_dir, filename + series_suffix.format(1) + '.tif'), shape=(t, z, c, reader.sizes['y'], reader.sizes['x']), dtype=reader.pixel_type, imagej=True)

    for idx, img in enumerate(reader):
        if alignment:
            # get channels for alignment
            img0 = img[alignment_channel_cam1]
            img1 = img[alignment_channel_cam2]

            if 'z' in reader.bundle_axes:
                img0 = np.max(img0, axis=0)
                img1 = np.max(img1, axis=0)
            
            # align
            model = align_orb_ransac_cv2(img0, img1)

            if model is None:
                print('Not enough correspondences found, skipping image {}, series {}.'.format(path, idx), flush=True)
                continue
        
        # collect all channels
        res = []
        for ch, chimg in enumerate(img):  
            img_ = chimg 
            # transform if channel belongs to camera 2
            if alignment and ch in channels_cam2 and ch != alignment_channel_cam2:
                img_ = transform_planewise(img_, model, reader.bundle_axes)

            if ch not in remove_channels:        
                res.append(img_)
            
        # stack along axis 1 for ImageJ-compatible ZCYX output
        if 'z' in reader.bundle_axes:
            res = np.stack(res, axis=1)
        else:
            res = np.stack(res, axis=0)
            res = np.expand_dims(res, axis=1)
        
        folderidx = idx // t + 1
        fileidx = (idx - (folderidx-1) * t) + 1
        if video_split:
            # get filename before suffix
            h,ta = os.path.split(path)
            filename = ta.rsplit('.',1)[0]

            if not os.path.exists(os.path.join(out_dir, filename + '_series' + str(folderidx) + '_single_frames')):
                os.makedirs(os.path.join(out_dir, filename + '_series' + str(folderidx) + '_single_frames'))
            
            # construct new filename
            outfile = os.path.join(out_dir, filename + '_series' + str(folderidx) + '_single_frames', filename + series_suffix.format(folderidx) + '_slice{}'.format(fileidx) + '.tif')
                        
            # save as ImageJ-compatible tiff stack
            imsave(outfile, res, imagej=True)

        else:
            imagestack[idx - t * idx//t] = res
            imagestack.flush()
        
            if (idx+1) % t == 0 and t != 1:
                # Generate new tiff file
            
                folderidx = (idx+1) // t + 1

                # get filename before suffix
                h,ta = os.path.split(path)
                filename = ta.rsplit('.',1)[0]
                
                # construct new filename
                outfile = os.path.join(out_dir, filename + series_suffix.format(folderidx) + '.tif')

                imagestack = memmap(outfile, shape=(t, z, c, reader.sizes['y'], reader.sizes['x']), dtype=reader.pixel_type, imagej=True)


