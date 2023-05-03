import os
import pymongo
import datetime
import tarfile
import io
import boto3
import shutil
import json
import base64
from bson import ObjectId
from bson import Binary

def lambda_handler(event, context):
    client = pymongo.MongoClient(os.environ['MONGODB_URI'])
    db = client[os.environ['MONGODB_NAME']]
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    backup_dir = '/tmp/sanjay1-backup-directory'

    # Insert data into mongodb database
    collection = db['mycollection']
    document = {'name': 'sanjay', 'age': 30, 'city': 'New York'}
    result = collection.insert_one(document)
    print('Document inserted with id:', result.inserted_id)

    # Remove backup directory if exists and create new
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
    os.makedirs(backup_dir)
    os.chdir(backup_dir)

    # backup file name
    backup_name = f'{os.environ["MONGODB_NAME"]}_{timestamp}.tar.gz'
    with tarfile.open(backup_name, 'w:gz') as tar:
        for collection_name in db.list_collection_names():
            collection = db[collection_name]
            for doc in collection.find():
                doc['_id'] = str(doc['_id'])
                for key, value in doc.items():
                    if isinstance(value, Binary):
                        doc[key] = bytes(value).decode('latin-1')
                file_name = f'{os.environ["MONGODB_NAME"]}/{collection_name}/{doc["_id"]}.json'
                # Convert UUID to string before serialization
                doc = json.loads(json.dumps(doc, default=str))
                file_data = io.BytesIO(json.dumps(doc).encode())
                tarinfo = tarfile.TarInfo(name=file_name)
                tarinfo.size = len(file_data.getvalue())
                tar.addfile(tarinfo, file_data)

    s3 = boto3.client('s3')
    with open(backup_name, 'rb') as backup_file:
        s3.upload_fileobj(io.BytesIO(backup_file.read()), os.environ['S3_BUCKET_NAME'], backup_name)
    os.remove(backup_name)
