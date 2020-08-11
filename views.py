import os

from flask import render_template
from flask import request, jsonify

from app import app
from tasks import align_task, detect_task, mask_task

import logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['POST'])
def queue_job():
    logging.info(request.json)

    detect = False
    mask = False
    if 'detect' in request.json.keys():
        detect = True
    if 'mask' in request.json.keys():
        mask = True
    
    if 'align' in request.json.keys():
        in_dir = request.json['path']
        out_dir = os.path.join(in_dir, 'aligned')

        alignment = request.json['align']['alignment']
        video_split = request.json['align']['videoSplit']
        channels = request.json['align']['channels'] 
        file_format = request.json['align']['inputFileFormat'] 
        dimensions = request.json['align']['dimensions']

        task = align_task(in_dir, out_dir, detect, mask, alignment, video_split, channels, file_format, dimensions)

    elif detect:
        if 'mask' in request.json.keys():
            mask = True
        else:
            mask = False

        in_dir = os.path.join(request.json['path'], 'aligned')
        out_dir = os.path.join(request.json['path'], 'cropped')
        zproject = request.json['detect']['zproject']
        video_split = request.json['detect']['videoSplit']
        boxsize = request.json['detect']['boxsize']
        channels = request.json['detect']['channels']
        video = request.json['detect']['video']

        task = detect_task(in_dir, out_dir, mask, zproject, video_split, boxsize, channels, video)

    elif mask:
        in_dir = os.path.join(request.json['path'], 'cropped')
        out_dir = os.path.join(request.json['path'], 'masked')
        zproject = request.json['detect']['zproject']
        channels = request.json['detect']['channels']

        task = mask_task(in_dir, out_dir, zproject, channels)

    return 'Queued, success'

@app.route('/', methods=['GET'])
def get_progress():
    pass
