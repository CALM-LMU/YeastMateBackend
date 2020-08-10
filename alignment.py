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
from skimage.external.tifffile import imsave
from skimage.feature import register_translation
from skimage.feature import match_descriptors, ORB, plot_matches
from skimage.transform import AffineTransform, EuclideanTransform


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


def process_single_file(counter, path, out_dir, alignment="True", video_split="False", file_format='.nd2', tif_channels=None, remove_channels=None, series_suffix='_series{}',
                        channels_cam1=(0,2), channels_cam2=(1,3),
                        alignment_channel_cam1=0,           
                        alignment_channel_cam2=1):
    
    # create output dir, if it does not exist yet
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    if file_format == '.nd2':
        reader = pims.open(path)

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
        bundleax += 'yx'

        total = m * t

        reader.bundle_axes = bundleax
        reader.iter_axes = iterax

        savepoint = t - 1
        
        # go through single images
        timestack = []
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
            imgs = []
            for ch, chimg in enumerate(img):  
                img_ = chimg 
                if alignment:
                    # transform if channel belongs to camera 2
                    if ch in channels_cam2 and ch != alignment_channel_cam2:
                        img_ = transform_planewise(img_, model, reader.bundle_axes)

                if ch not in remove_channels:        
                    	imgs.append(img_)
            
            progress = (idx+1) / total * 100
            progress = progress / counter['total'] * (counter['idx']+1)
                
            # stack along axis 1 for ImageJ-compatible ZCXY output
            if 'z' in reader.bundle_axes:
                res = np.stack(imgs, axis=1)
            else:
                res = np.stack(imgs, axis=0)

            timestack.append(res)
            
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
      
            if idx % savepoint == 0 and fileidx != 1:
                folderidx = idx // t + 1

                res = np.asarray(timestack)

                # get filename before suffix
                h,ta = os.path.split(path)
                filename = ta.rsplit('.',1)[0]
                
                # construct new filename
                outfile = os.path.join(out_dir, filename + series_suffix.format(folderidx) + '.tif')
                            
                # save as ImageJ-compatible tiff stack
                imsave(outfile, res, imagej=True)

                timestack = []

    else:
        if alignment:          
            image = imread(path)

            correct_order = {'f': 0, 't': 1, 'c': 2, 'z':3, 'h':4, 'w':5}

            try:
                if tif_channels['f'] is None:
                    tif_channels['f'] = len(correct_order.values()) + 1
                    image = np.expand_dims(image, axis=-1)

                if tif_channels['t'] is None:
                    tif_channels['t'] = len(correct_order.values()) + 1
                    image = np.expand_dims(image, axis=-1)
                
                if tif_channels['z'] is None:
                    z_stack = False

                    tif_channels['f'] = len(correct_order.values()) + 1
                    image = np.expand_dims(image, axis=-1)
                else:
                    z_stack = True

                new_order = []
                for k in correct_order.keys():
                    new_order.append(tif_channels[k])

                image = np.transpose(image, new_order)

            except:
                print('Order of tif_channels was invalid! Can not perform alignment!', flush=True)

            for idf, fov in enumerate(image):
                timestack = []
                for idt,tp in enumerate(fov):
                    img0 = tp[alignment_channel_cam1]
                    img1 = tp[alignment_channel_cam2]

                    if z_stack:
                        img0 = np.max(img0, axis=0)
                        img1 = np.max(img1, axis=0)
                    else:
                        img0 = img0[0]
                        img1 = img1[0]

                    # align
                    model = align_orb_ransac_cv2(img0, img1)

                    if model is None:
                        print('Not enough correspondences found, skipping image {}, series {}.'.format(path, idf*idt), flush=True)
                        # TODO Add logfile here for skipped files!
                        continue

                    # collect all channels
                    imgs = []
                    for ch in range(tp.shape[0]):   
                        img_ = tp[ch]

                        # transform if channel belongs to camera 2
                        if ch in channels_cam2:
                            img_ = transform_planewise(img_, model)
                    
                        imgs.append(img_)
                        
                    # stack along axis 1 for ImageJ-compatible ZCXY output
                    res = np.asarray(imgs)
                    res = np.swapaxes(res, 0, 1)

                    # remove no longer necessary channels
                    if remove_channels is not None:
                        res = np.delete(res, remove_channels, axis=1)

                    progress = (idf+1)*(idt+1) / total * 100
                    progress = progress / counter['total'] * (counter['idx']+1)

                    if video_split:
                        # get filename before suffix
                        h,ta = os.path.split(path)
                        filename = ta.rsplit('.',1)[0]

                        if not os.path.exists(os.path.join(out_dir, filename + '_series' + str(idf) + '_single_frames')):
                            os.makedirs(os.path.join(out_dir, filename + '_series' + str(idf) + '_single_frames'))
                        
                        # construct new filename
                        outfile = os.path.join(out_dir, filename + '_series' + str(idf) + '_single_frames', filename + series_suffix.format(idf) + '_slice{}'.format(idt) + '.tif')
                                        
                        # save as ImageJ-compatible tiff stack
                        imsave(outfile, res, imagej=True)

                    timestack.append(res)

                res = np.asarray(timestack)
            
                # get filename before suffix
                h,ta = os.path.split(path)
                filename = ta.rsplit('.',1)[0]
                
                # construct new filename
                outfile = os.path.join(out_dir, filename + series_suffix.format(idf) + '.tif')
                                
                # save as ImageJ-compatible tiff stack
                imsave(outfile, res, imagej=True)

            print('Image is already a tif file! Skipping process.', flush=True)
