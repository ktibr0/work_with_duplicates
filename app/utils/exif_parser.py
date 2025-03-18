import exifread
import logging
from datetime import datetime
import re

class ExifParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_exif(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            if not tags:
                return {}
            exif_data = self._process_exif_tags(tags)
            return exif_data
        except Exception as e:
            self.logger.error(f"Ошибка при чтении EXIF из {file_path}: {e}")
            return {}
    
    def _process_exif_tags(self, tags):
        exif_data = {}
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
                value = str(tags[tag])
                # Обработка кракозябр (удаление непечатаемых символов)
                value = self._sanitize_exif_value(value)
                exif_data[key] = value
        
        if 'DateTimeOriginal' in exif_data:
            try:
                dt = datetime.strptime(exif_data['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
                exif_data['FormattedDate'] = dt.strftime('%d.%m.%Y %H:%M:%S')
            except Exception:
                pass
        
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
    
    def _sanitize_exif_value(self, value):
        """Очистка кракозябр и некорректных символов в EXIF данных"""
        # Заменяем непечатаемые и некорректно закодированные символы
        value = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)
        # Если строка содержит больше 50% нелатинских символов и не является кириллицей
        non_latin = re.findall(r'[^\x00-\x7F\u0400-\u04FF]', value)
        if non_latin and len(non_latin) > len(value) * 0.5:
            # Вероятно, это кракозябры - заменяем на стандартный текст
            return "[Некорректно закодированный текст]"
        return value
    
    def _convert_to_degrees(self, value):
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)
    
    def compare_exif(self, exif1, exif2):
        differences = {}
        all_keys = set(exif1.keys()) | set(exif2.keys())
        for key in all_keys:
            if key not in exif1:
                differences[key] = {'file1': None, 'file2': exif2[key]}
            elif key not in exif2:
                differences[key] = {'file1': exif1[key], 'file2': None}
            elif exif1[key] != exif2[key]:
                differences[key] = {'file1': exif1[key], 'file2': exif2[key]}
        return differences
    
    def get_exif_display_name(self, tag_key):
        """Возвращает человекочитаемые названия EXIF-тегов"""
        display_names = {
            'Model': 'Модель',
            'Make': 'Производитель',
            'DateTime': 'Дата и время',
            'DateTimeOriginal': 'Дата и время оригинала',
            'FormattedDate': 'Форматированная дата',
            'ExposureTime': 'Выдержка',
            'FNumber': 'Диафрагма',
            'ISOSpeedRatings': 'ISO',
            'FocalLength': 'Фокусное расстояние',
            'ExposureProgram': 'Программа экспозиции',
            'Flash': 'Вспышка',
            'Orientation': 'Ориентация',
            'XResolution': 'Разрешение X',
            'YResolution': 'Разрешение Y',
            'Software': 'Программное обеспечение',
            'GPSLatitude': 'Широта',
            'GPSLongitude': 'Долгота',
            'GPSLatitudeRef': 'Направление широты',
            'GPSLongitudeRef': 'Направление долготы',
            'GPSCoordinates': 'GPS координаты',
            'MapLink': 'Ссылка на карту'
        }
        return display_names.get(tag_key, tag_key)