import urllib.request
import urllib.error

try:
    req = urllib.request.Request('http://127.0.0.1:5000/api/face/capture', data=b'', method='POST')
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print(e.read().decode())
