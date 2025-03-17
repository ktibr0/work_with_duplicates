# app/models.py
from pymongo import MongoClient
import datetime

class Database:
    """Класс для работы с базой данных MongoDB"""
    
    def __init__(self, uri="mongodb://mongodb:27017/"):
        self.client = MongoClient(uri)
        self.db = self.client.photo_duplicates
        
    def save_scan_session(self, directories):
        """
        Сохраняет информацию о сессии сканирования
        
        Args:
            directories (list): Список директорий для сканирования
            
        Returns:
            str: ID сессии
        """
        session = {
            'directories': directories,
            'created_at': datetime.datetime.utcnow(),
            'status': 'started'
        }
        
        result = self.db.scan_sessions.insert_one(session)
        return str(result.inserted_id)
        
    def save_duplicates(self, session_id, duplicates):
        """
        Сохраняет найденные дубликаты в базу данных
        
        Args:
            session_id (str): ID сессии сканирования
            duplicates (dict): Словарь групп дубликатов
            
        Returns:
            int: Количество сохраненных групп
        """
        # # Преобразуем строку в ObjectId, если необходимо
        # if isinstance(session_id, str) and len(session_id) == 24:
            # session_id = ObjectId(session_id)
            
        # Обновляем статус сессии
        self.db.scan_sessions.update_one(
            {'_id': session_id},
            {'$set': {'status': 'processing'}}
        )
        
        # Сохраняем группы дубликатов
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
        
        # Обновляем статус сессии
        self.db.scan_sessions.update_one(
            {'_id': session_id},
            {'$set': {'status': 'completed', 'completed_at': datetime.datetime.utcnow()}}
        )
        
        return len(duplicate_groups)
        
    def get_session_duplicates(self, session_id):
        """
        Получает все группы дубликатов для сессии
        
        Args:
            session_id (str): ID сессии
            
        Returns:
            list: Список групп дубликатов
        """
        return list(self.db.duplicate_groups.find({'session_id': session_id}))