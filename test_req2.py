import urllib.request, json
import urllib.error

data = json.dumps({'image_path': 'non_existent'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:5000/api/face/recognize', data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print(e.read().decode())