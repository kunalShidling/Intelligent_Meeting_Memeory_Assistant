import sys
sys.path.append('opencv')
from database import FaceDatabase
db = FaceDatabase()
db.connect()
db.collection.update_one({'name': 'karthik'}, {'$set': {'image_path': None}})
