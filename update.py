import sys
sys.path.append('opencv')
from database import FaceDatabase
db = FaceDatabase()
db.connect()
db.collection.update_one({'name': 'karthik'}, {'$set': {'image_path': r'D:\miniproject\meeting_data\images\capture_20260310_230839.jpg'}})
