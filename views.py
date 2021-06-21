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
    alignment  = False
    detection = False
    export = False

    if 'preprocessing' in request.json.keys():
        alignment = True
        path = os.path.join(request.json['path'])
    if 'detection' in request.json.keys():
        detection = True
        path = os.path.join(request.json['path'])
    if 'export' in request.json.keys():
        export = True
        path = os.path.join(request.json['path'])

    pipeline = start_pipeline.s(alignment, detection, export, path)
    
    if 'preprocessing' in request.json.keys():
        path = os.path.join(request.json['path'])

        alignment = request.json['preprocessing']['alignment']
        channels = request.json['preprocessing']['channels'] 
        file_format = request.json['preprocessing']['inputFileFormat'] 
        dimensions = request.json['preprocessing']['dimensions']
        video_split = request.json['preprocessing']['videoSplit']

        pipeline = pipeline.then(preprocessing_task, path, detection, export, alignment, channels, file_format, dimensions, video_split)

    if 'detection' in request.json.keys():
        path = os.path.join(request.json['path'])
        
        include_tag = request.json['includeTag']
        exclude_tag = request.json['excludeTag']

        zstack = request.json['detection']['zstack']
        video = request.json['detection']['video']
        graychannel = int(request.json['detection']['graychannel'])
        scale_factor = float(request.json['detection']['scaleFactor'])
        frame_selection = request.json['detection']['frameSelection']
        ip = request.json['detection']['ip']

        pipeline = pipeline.then(detect_task, path, export, include_tag, exclude_tag, zstack, graychannel, scale_factor, video, frame_selection, ip)

    if 'export' in request.json.keys():
        path = os.path.join(request.json['path'])

        crop = request.json['export']['crop']
        measure = request.json['export']['measure']
        classes = request.json['export']['classes']
        video = request.json['export']['video']
        video_split = request.json['export']['videoSplit']
        score_threshold = float(request.json['export']['scoreThreshold'])
        boxsize = int(request.json['export']['boxsize'])
        box_expansion = request.json['export']['boxExpansion']

        pipeline = pipeline.then(export_task, path, measure, crop, classes, video, video_split, score_threshold, box_expansion, boxsize)

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
