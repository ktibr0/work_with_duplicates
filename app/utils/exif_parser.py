# app/utils/exif_parser.py
import exifread
import logging
from datetime import datetime

class ExifParser:
    """Класс для обработки EXIF-метаданных фотографий"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_exif(self, file_path):
        """
        Извлекает EXIF-метаданные из файла
        
        Args:
            file_path (str): Путь к файлу
            
        Returns:
            dict: Словарь с обработанными EXIF-метаданными
        """
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            
            if not tags:
                return {}
            
            # Извлекаем основные метаданные
            exif_data = self._process_exif_tags(tags)
            return exif_data
            
        except Exception as e:
            self.logger.error(f"Ошибка при чтении EXIF из {file_path}: {e}")
            return {}
    
    def _process_exif_tags(self, tags):
        """
        Обрабатывает теги EXIF и возвращает структурированный словарь
        
        Args:
            tags (dict): Словарь с тегами EXIF
            
        Returns:
            dict: Обработанные теги EXIF
        """
        exif_data = {}
        
        # Обработка основных тегов
        exif_mappings = {
            'Model': 'EXIF Model',
            'Make': 'EXIF Make',
            'DateTime': 'Image DateTime',
            'DateTimeOriginal': 'EXIF DateTimeOriginal',
            'ExposureTime': 'EXIF ExposureTime',
            'FNumber': 'EXIF FNumber',
            'ISOSpeedRatings': 'EXIF ISOSpeedRatings',
            'FocalLength': 'EXIF FocalLength',
            'ExposureProgram': 'EXIF ExposureProgram',
            'Flash': 'EXIF Flash',
            'Orientation': 'Image Orientation',
            'XResolution': 'Image XResolution',
            'YResolution': 'Image YResolution',
            'Software': 'Image Software',
            'GPSLatitude': 'GPS GPSLatitude',
            'GPSLongitude': 'GPS GPSLongitude',
            'GPSLatitudeRef': 'GPS GPSLatitudeRef',
            'GPSLongitudeRef': 'GPS GPSLongitudeRef'
        }
        
        for key, tag in exif_mappings.items():
            if tag in tags:
                exif_data[key] = str(tags[tag])
        
        # Обработка даты и времени
        if 'DateTimeOriginal' in exif_data:
            try:
                dt = datetime.strptime(exif_data['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
                exif_data['FormattedDate'] = dt.strftime('%d.%m.%Y %H:%M:%S')
            except Exception:
                pass
        
        # Обработка GPS-координат
        if 'GPSLatitude' in exif_data and 'GPSLongitude' in exif_data:
            try:
                lat = self._convert_to_degrees(tags['GPS GPSLatitude'])
                lon = self._convert_to_degrees(tags['GPS GPSLongitude'])
                
                if 'GPSLatitudeRef' in exif_data and exif_data['GPSLatitudeRef'] == 'S':
                    lat = -lat
                if 'GPSLongitudeRef' in exif_data and exif_data['GPSLongitudeRef'] == 'W':
                    lon = -lon
                
                exif_data['GPSCoordinates'] = f"{lat:.6f}, {lon:.6f}"
                exif_data['MapLink'] = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
            except Exception as e:
                self.logger.error(f"Ошибка при обработке GPS-координат: {e}")
        
        return exif_data
    
    def _convert_to_degrees(self, value):
        """
        Преобразует GPS-координаты из формата EXIF в десятичные градусы
        
        Args:
            value: Значение GPS-координаты в формате EXIF
            
        Returns:
            float: Координата в десятичных градусах
        """
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        
        return d + (m / 60.0) + (s / 3600.0)
    
    def compare_exif(self, exif1, exif2):
        """
        Сравнивает два набора EXIF-метаданных и возвращает различия
        
        Args:
            exif1 (dict): Первый набор EXIF-метаданных
            exif2 (dict): Второй набор EXIF-метаданных
            
        Returns:
            dict: Словарь с различиями
        """
        differences = {}
        
        # Объединяем ключи из обоих словарей
        all_keys = set(exif1.keys()) | set(exif2.keys())
        
        for key in all_keys:
            # Если ключ есть только в одном из словарей
            if key not in exif1:
                differences[key] = {'file1': None, 'file2': exif2[key]}
            elif key not in exif2:
                differences[key] = {'file1': exif1[key], 'file2': None}
            # Если значения различаются
            elif exif1[key] != exif2[key]:
                differences[key] = {'file1': exif1[key], 'file2': exif2[key]}
        
        return differences