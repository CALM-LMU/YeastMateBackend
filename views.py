import os
import copy
import json

from flask import render_template
from flask import request, jsonify

from app import app
from tasks import start_pipeline, preprocessing_task, detect_task, export_task

from app import huey

import logging
logging.basicConfig(level=logging.DEBUG)

@huey.pre_execute()
def add_execute_task(task):
    global executing_tasks

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

@app.route('/', methods=['POST'])
def queue_job():

    path = os.path.join(request.json['path'])
    pipeline = start_pipeline.s()
    
    if 'preprocessing' in request.json.keys():
        alignment = request.json['preprocessing']['alignment']
        channels = request.json['preprocessing']['channels'] 
        video_split = request.json['preprocessing']['videoSplit']

        pipeline = pipeline.then(preprocessing_task, path, alignment, channels, video_split)

    if 'detection' in request.json.keys():      
        include_tag = request.json['includeTag']
        exclude_tag = request.json['excludeTag']
        
        advanced_settings = request.json['detection']['advancedSettings']
        super_advanced_settings = request.json['detection']['superAdvancedSettings']
        zstack = request.json['detection']['zstack']
        zslice = int(request.json['detection']['zSlice']) / 100
        video = request.json['detection']['video']
        frame_selection = request.json['detection']['frameSelection']
        multichannel = request.json['detection']['channelSwitch']
        graychannel = int(request.json['detection']['graychannel'])
        pixel_size = float(request.json['detection']['pixelSize'])
        lower_quantile = int(request.json['detection']['lowerQuantile'])
        upper_quantile = int(request.json['detection']['upperQuantile'])
        single_threshold = int(request.json['detection']['singleThreshold']) / 100
        mating_threshold = int(request.json['detection']['matingThreshold']) / 100
        budding_threshold = int(request.json['detection']['buddingThreshold']) / 100
        ip = request.json['detection']['ip']
        ref_pixel_size = int(request.json['detection']['referencePixelSize'])

        if not super_advanced_settings:
            ref_pixel_size = 110

        if not advanced_settings:
            score_thresholds = {0:0.9, 1:0.75, 2:0.75}

            lower_quantile = 2
            upper_quantile = 98
            pixel_size = 110

        else:
            score_thresholds = {0:single_threshold, 1:mating_threshold, 2:budding_threshold}

        pipeline = pipeline.then(detect_task, path, include_tag, exclude_tag, zstack, zslice, multichannel, graychannel, lower_quantile, upper_quantile, score_thresholds, pixel_size, video, frame_selection, ip, ref_pixel_size)

    if 'export' in request.json.keys():
        crop = request.json['export']['crop']
        classes = request.json['export']['classes']
        boxsize = int(request.json['export']['boxSize'])
        box_expansion = request.json['export']['boxExpansion']
        boxscale = float(request.json['export']['boxScale'])
        boxscale_switch = request.json['export']['boxScaleSwitch']

        pipeline = pipeline.then(export_task, path, crop, classes, box_expansion, boxsize, boxscale_switch, boxscale)

    huey.enqueue(pipeline)

    return 'Queued, success'

@app.route('/', methods=['GET'])
def get_tasklist():
    tasklist = list(json.loads(huey.storage.peek_data('tasks')).values())

    tasks = huey.pending()
    for t in tasks:
        if t.name == 'start_pipeline':
            if t.args[0]:
                job = 'Preprocessing'
                tasklist.append({'Job': job, 'Path': t.args[3], 'Status': 'Pending'})
            
            if t.args[1]:
                job = 'Detection'
                tasklist.append({'Job': job, 'Path': t.args[3], 'Status': 'Pending'})
            
            if t.args[2]:
                job = 'Export'
                tasklist.append({'Job': job, 'Path': t.args[3], 'Status': 'Pending'})
  
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
