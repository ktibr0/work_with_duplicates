# app/models.py
from pymongo import MongoClient
import datetime
class Database:
    def __init__(self, uri="mongodb://mongodb:27017/"):
        self.client = MongoClient(uri)
        self.db = self.client.photo_duplicates
    def save_scan_session(self, directories):
        session = {
            'directories': directories,
            'created_at': datetime.datetime.utcnow(),
            'status': 'started'
        }
        result = self.db.scan_sessions.insert_one(session)
        return str(result.inserted_id)
    def save_duplicates(self, session_id, duplicates):
        self.db.scan_sessions.update_one(
            {'_id': session_id},
            {'$set': {'status': 'processing'}}
        )
        duplicate_groups = []
        for filename, files in duplicates.items():
            group = {
                'session_id': session_id,
                'filename': filename,
                'files': files,
                'created_at': datetime.datetime.utcnow()
            }
            duplicate_groups.append(group)
        if duplicate_groups:
            self.db.duplicate_groups.insert_many(duplicate_groups)
        self.db.scan_sessions.update_one(
            {'_id': session_id},
            {'$set': {'status': 'completed', 'completed_at': datetime.datetime.utcnow()}}
        )
        return len(duplicate_groups)
    def get_session_duplicates(self, session_id):
        return list(self.db.duplicate_groups.find({'session_id': session_id}))
    
    def save_marked_files(self, session_id, files):
        result = self.db.marked_files.update_one(
            {'session_id': session_id},
            {
                '$set': {
                    'files': files,
                    'updated_at': datetime.datetime.utcnow()
                }
            },
            upsert=True
        )
        return result
        
    def get_marked_files(self, session_id):
        doc = self.db.marked_files.find_one({'session_id': session_id})
        if doc:
            return doc.get('files', [])
        return []
        
    def clear_marked_files(self, session_id):
        return self.db.marked_files.delete_one({'session_id': session_id})        