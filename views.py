import os

from flask import render_template
from flask import request, jsonify

from app import app
from tasks import align_task

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

        alignment = request.json['align']['alignment']s
        video_split = request.json['align']['videoSplit']
        channels = request.json['align']['channels'] 
        file_format = request.json['align']['inputFileFormat'] 
        dimensions = request.json['align']['dimensions']

        task = align_task(in_dir, out_dir, detect, mask, alignment, video_split, channels, file_format, dimensions)

    elif detect:
        pass

    elif mask:
        pass

    return 'Queued, success'

@app.route('/', methods=['GET'])
def get_progress():
    pass
