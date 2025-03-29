# app/utils/file_scanner.py
import os
from pathlib import Path
from PIL import Image
import concurrent.futures
import logging
from app.utils.exif_parser import ExifParser
class FileScanner:
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
        self.exif_parser = ExifParser()
    def scan_directories(self, directories, extensions=('.jpg', '.jpeg', '.png', '.tiff', '.bmp')):
        file_map = {}
        for directory_index, directory in enumerate(directories):
            self.logger.info(f"Сканирование директории: {directory}")
            base_path = Path(directory)
            if not base_path.exists():
                self.logger.error(f"Директория не существует: {directory}")
                continue
            for root, _, files in os.walk(base_path):
                for filename in files:
                    if not filename.lower().endswith(extensions):
                        continue
                    file_path = Path(root) / filename
                    if filename not in file_map:
                        file_map[filename] = []
                    try:
                        file_info = self._get_file_info(file_path, directory_index)
                        file_map[filename].append(file_info)
                    except Exception as e:
                        self.logger.error(f"Ошибка при обработке файла {file_path}: {e}")
        duplicates = {name: files for name, files in file_map.items() if len(files) > 1}
        return duplicates
    def _get_file_info(self, file_path, directory_index):
        file_stat = file_path.stat()
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format = img.format
        except Exception as e:
            self.logger.warning(f"Не удалось получить размер изображения {file_path}: {e}")
            width, height, format = 0, 0, "Unknown"
        exif_data = self.exif_parser.extract_exif(str(file_path))
        return {
            'path': str(file_path),
            'name': file_path.name,
            'size': file_stat.st_size,
            'modified': file_stat.st_mtime,
            'width': width,
            'height': height,
            'format': format,
            'exif': exif_data,
            'directory_index': directory_index
        }
    def generate_preview(self, file_path, size=(300, 300)):
        try:
            with Image.open(file_path) as img:
                img_copy = img.copy()
                img_copy.thumbnail(size)
                from io import BytesIO
                import base64
                buffer = BytesIO()
                img_copy.save(buffer, format='JPEG')
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Ошибка при создании превью для {file_path}: {e}")
            return None
    def compare_duplicates(self, files):
        if len(files) < 2:
            return {}
        differences = {}
        for i in range(len(files)):
            for j in range(i+1, len(files)):
                file1 = files[i]
                file2 = files[j]
                exif_diff = self.exif_parser.compare_exif(file1['exif'], file2['exif'])
                if exif_diff:
                    key = f"{i}_{j}"
                    differences[key] = {
                        'file1': file1['path'],
                        'file2': file2['path'],
                        'differences': exif_diff
                    }
        return differences