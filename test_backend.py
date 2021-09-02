import requests

request_json = {'path': '/Users/david/Desktop/ym_test',
      'includeTag': '',
      'excludeTag': '',
      'detection': {
          'advancedSettings': False,
          'superAdvancedSettings': False,
          'zstack': False,
          'video': False,
          'channelSwitch': False,
          'zSlice' : 0,
          'frameSelection': '',
          'graychannel': 0,
          'pixelSize': 110,
          'lowerQuantile': 1,
          'upperQuantile': 99,
          'singleThreshold': 90,
          'matingThreshold': 75,
          'buddingThreshold': 75,
          'referencePixelSize': 110,
          'ip' : 'localhost:11005'
      }
}

requests.post('http://localhost:11002', json=request_json)