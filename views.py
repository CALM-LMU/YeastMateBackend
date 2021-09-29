import os
import copy
import json

from http import HTTPStatus

from flask import render_template
from flask import request, jsonify

from yeastmatedetector import __version__ as yeastmate_version

from app import app, huey
from tasks import start_pipeline, preprocessing_task, detect_task, export_task

import logging
logging.basicConfig(level=logging.DEBUG)

@huey.pre_execute()
def add_execute_task(task):
    tasks = json.loads(huey.storage.peek_data('tasks'))

    if task.name == 'preprocessing_task':
        tasks[task.id+'preprocessing'] = {'Job': 'Preprocessing', 'Path': task.args[0], 'Status': 'Running'}

        if task.args[1]:
            tasks[task.id+'detect'] = {'Job': 'Detection', 'Path': task.args[0], 'Status': 'Pending'}

    elif task.name == 'detect_task':
        tasks[task.id+'detect'] = {'Job': 'Detection', 'Path': task.args[0], 'Status': 'Running'}

    else:
        return

    huey.storage.put_data('tasks', json.dumps(tasks).encode('utf-8'))

@huey.post_execute()
def remove_execute_task(task, task_value, exc):
    if task.name != 'start_pipeline':
        tasks = json.loads(huey.storage.peek_data('tasks'))
        try:
            del tasks[task.id+'preprocessing']
        except:
            pass

        try:
            del tasks[task.id+'detect']
        except:
            pass

        huey.storage.put_data('tasks', json.dumps(tasks).encode('utf-8'))

@app.route('/submit', methods=['POST'])
def queue_job():

    alignment  = False
    detection = False
    export = False

    if 'preprocessing' in request.json.keys():
        alignment = True
    if 'detection' in request.json.keys():
        detection = True
    if 'export' in request.json.keys():
        export = True

    path = os.path.join(request.json['path'])
    pipeline = start_pipeline.s(path, alignment, detection, export)
    
    if 'preprocessing' in request.json.keys():
        alignment = request.json['preprocessing']['alignment']
        channels = request.json['preprocessing']['channels'] 
        video_split = request.json['preprocessing']['videoSplit']

        pipeline = pipeline.then(preprocessing_task, path, detection, export, alignment, channels, video_split)

    if 'detection' in request.json.keys():      
        include_tag = request.json['includeTag']
        exclude_tag = request.json['excludeTag']
        
        advanced_settings = request.json['detection']['advancedSettings']
        zstack = request.json['detection']['zstack']
        zslice = float(request.json['detection']['zSlice']) / 100
        video = request.json['detection']['video']
        frame_selection = request.json['detection']['frameSelection']
        multichannel = request.json['detection']['channelSwitch']
        graychannel = int(request.json['detection']['graychannel'])
        pixel_size = float(request.json['detection']['pixelSize'])
        ref_pixel_size = float(request.json['detection']['referencePixelSize'])
        lower_quantile = float(request.json['detection']['lowerQuantile'])
        upper_quantile = float(request.json['detection']['upperQuantile'])
        single_threshold = float(request.json['detection']['singleThreshold']) / 100
        mating_threshold = float(request.json['detection']['matingThreshold']) / 100
        budding_threshold = float(request.json['detection']['buddingThreshold']) / 100

        ip = request.json['backend']['detectionIP']
        port = request.json['backend']['detectionPort']

        if not advanced_settings:
            score_thresholds = {0:0.9, 1:0.75, 2:0.75}

            lower_quantile = 1.5
            upper_quantile = 98.5

        else:
            score_thresholds = {0:single_threshold, 1:mating_threshold, 2:budding_threshold}

        pipeline = pipeline.then(detect_task, path, export, include_tag, exclude_tag, zstack, zslice, multichannel, graychannel, lower_quantile, upper_quantile, score_thresholds, pixel_size, ref_pixel_size, video, frame_selection, ip, port)

    if 'export' in request.json.keys():
        classes = request.json['export']['classes']
        keep_id = request.json['export']['keepID']
        boxsize = int(request.json['export']['boxSize'])
        box_expansion = request.json['export']['boxExpansion']
        boxscale = float(request.json['export']['boxScale'])
        boxscale_switch = request.json['export']['boxScaleSwitch']

        pipeline = pipeline.then(export_task, path, classes, keep_id, box_expansion, boxsize, boxscale_switch, boxscale)

    huey.enqueue(pipeline)

    return 'Queued, success'

@app.route('/status', methods=['GET'])
def get_status():
    return {
            'name': 'YeastMate',
            'version': yeastmate_version
        }, HTTPStatus.OK

@app.route('/tasks', methods=['GET'])
def get_tasklist():
    tasklist = list(json.loads(huey.storage.peek_data('tasks')).values())

    tasks = huey.pending()
    for t in tasks:
        if t.name == 'start_pipeline':
            if t.args[1]:
                job = 'Preprocessing'
                tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})
            
            if t.args[2]:
                job = 'Detection'
                tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})
            
            if t.args[3]:
                job = 'Export'
                tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})
  
        if t.name == 'preprocessing_task':
            job = 'Preprocessing'
            tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})
            
            if t.args[1]:
                job = 'Detection'
                tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})

            if t.args[2]:
                job = 'Export'
                tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})

        elif t.name == 'detect_task':
            job = 'Detection'
            tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})

            if t.args[1]:
                job = 'Export'
                tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})

        elif t.name == 'export_task':
            job = 'Export'
            tasklist.append({'Job': job, 'Path': t.args[0], 'Status': 'Pending'})

        else:
            continue

    return jsonify({'tasks' : tasklist})
