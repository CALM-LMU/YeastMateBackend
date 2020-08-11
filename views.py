import os
import copy
import json

from flask import render_template
from flask import request, jsonify

from app import app
from tasks import align_task, detect_task, mask_task

from app import huey

import logging
logging.basicConfig(level=logging.DEBUG)


@huey.pre_execute()
def add_execute_task(task):
    global executing_tasks

    if task.name == 'align_task':
        job = 'Alignment'
    elif task.name == 'detect_task':
        job = 'Detection'
    elif task.name == 'mask_task':
        job = 'Masking'

    tasks = json.loads(huey.storage.peek_data('tasks'))
    tasks[task.id] = {'Job': job, 'Path': task.args[0], 'Status': 'Running'}
    huey.storage.put_data('tasks', json.dumps(tasks).encode('utf-8'))

@huey.post_execute()
def remove_execute_task(task, task_value, exc):
    tasks = json.loads(huey.storage.peek_data('tasks'))
    del tasks[task.id]
    huey.storage.put_data('tasks', json.dumps(tasks).encode('utf-8'))

@app.route('/', methods=['POST'])
def queue_job():
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
def get_tasklist():
    tasklist = list(json.loads(huey.storage.peek_data('tasks')).values())

    tasks = huey.pending()
    for t in tasks:
        if t.name == 'align_task':
            job = 'Alignment'
        elif t.name == 'detect_task':
            job = 'Detection'
        elif t.name == 'mask_task':
            job = 'Masking'

        tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})

    return jsonify({'tasks' : tasklist})
