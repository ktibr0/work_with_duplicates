# app/utils/samba_mounter.py
import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SambaMounter:
    def __init__(self, mount_base_dir='/mnt/samba'):
        self.mount_base_dir = Path(mount_base_dir)
        self.mount_points = {}
        os.makedirs(self.mount_base_dir, exist_ok=True)
        
    def mount_share(self, share_path, username=None, password=None):
        share_name = share_path.replace('/', '_').replace('\\', '_').strip('_')
        mount_point = self.mount_base_dir / share_name
        os.makedirs(mount_point, exist_ok=True)
        
        if share_path in self.mount_points:
            logger.info(f"Ресурс {share_path} уже примонтирован к {mount_point}")
            return str(mount_point)
            
        # Используем несколько опций для обеспечения доступа на запись
        mount_options = ['rw', 'uid='+str(os.getuid()), 'gid='+str(os.getgid()), 'file_mode=0777', 'dir_mode=0777']
        
        if username and password:
            mount_options.append(f'username={username},password={password}')
        
        options_str = ','.join(mount_options)
        
        try:
            logger.info(f"Монтирование {share_path} к {mount_point} с опциями: {options_str}")
            
            subprocess.run(
                ['mount', '-t', 'cifs', '-o', options_str, share_path, str(mount_point)],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            )
            
            self.mount_points[share_path] = mount_point
            logger.info(f"Успешно примонтирован {share_path} к {mount_point}")
            return str(mount_point)
        except subprocess.CalledProcessError as e:
            error_msg = f"Ошибка при монтировании {share_path}: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    def map_path(self, file_path):
        """Преобразует сетевой путь в локальный путь к примонтированному ресурсу"""
        # Проверяем точное совпадение
        for share_path, mount_point in self.mount_points.items():
            if file_path.startswith(share_path):
                mapped_path = file_path.replace(share_path, str(mount_point), 1)
                logger.info(f"Маппинг пути: {file_path} -> {mapped_path}")
                return mapped_path

        # Нормализуем пути (заменяем все слеши на стандартные для сравнения)
        normalized_file_path = file_path.replace('\\', '/')
        for share_path, mount_point in self.mount_points.items():
            normalized_share = share_path.replace('\\', '/')
            if normalized_file_path.startswith(normalized_share):
                mapped_path = normalized_file_path.replace(normalized_share, str(mount_point), 1)
                # Нормализуем результат для системы
                mapped_path = str(Path(mapped_path))
                logger.info(f"Маппинг пути (нормализованный): {file_path} -> {mapped_path}")
                return mapped_path
        
        # Проверяем другие варианты форматирования пути, например, с разными регистрами
        lower_file_path = normalized_file_path.lower()
        for share_path, mount_point in self.mount_points.items():
            lower_share = share_path.replace('\\', '/').lower()
            if lower_file_path.startswith(lower_share):
                # Важно! Используем оригинальную часть пути после маппинга
                rel_path = normalized_file_path[len(lower_share):]
                mapped_path = os.path.join(str(mount_point), rel_path.lstrip('/'))
                logger.info(f"Маппинг пути (регистронезависимый): {file_path} -> {mapped_path}")
                return mapped_path
        
        logger.warning(f"Не удалось выполнить маппинг пути: {file_path}, возвращаем исходный путь")
        return file_path
        
    def map_paths(self, file_paths):
        """Массовое преобразование путей"""
        return [self.map_path(path) for path in file_paths]
        
    def unmount_share(self, share_path):
        if share_path not in self.mount_points:
            return False
            
        mount_point = self.mount_points[share_path]
        try:
            logger.info(f"Размонтирование {share_path} от {mount_point}")
            subprocess.run(['umount', str(mount_point)], check=True)
            self.mount_points.pop(share_path)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при размонтировании {share_path}: {e}")
            # Не вызываем ошибку при размонтировании, просто логируем
            return False
            
    def unmount_all(self):
        """Размонтирует все примонтированные ранее ресурсы. 
        Продолжает попытки размонтирования даже если возникают ошибки."""
        success = True
        failed_shares = []
        
        # Пробуем размонтировать каждый ресурс
        for share_path in list(self.mount_points.keys()):
            try:
                if not self.unmount_share(share_path):
                    success = False
                    failed_shares.append(share_path)
            except Exception as e:
                logger.error(f"Исключение при размонтировании {share_path}: {e}")
                success = False
                failed_shares.append(share_path)
        
        # Если размонтирование не удалось, делаем более агрессивные попытки
        if failed_shares:
            logger.warning(f"Не удалось размонтировать ресурсы: {failed_shares}. Пробуем принудительно.")
            for share_path in failed_shares:
                try:
                    if share_path in self.mount_points:
                        mount_point = self.mount_points[share_path]
                        # Принудительное размонтирование с опцией -f (force)
                        subprocess.run(['umount', '-f', str(mount_point)], 
                                      check=False,  # Не выбрасываем исключение при ошибке
                                      stderr=subprocess.PIPE)
                        self.mount_points.pop(share_path, None)
                except Exception as e:
                    logger.error(f"Ошибка при принудительном размонтировании {share_path}: {e}")
        
        # Очищаем все оставшиеся записи
        self.mount_points.clear()
        return success

    def get_mount_status(self):
        """Возвращает информацию о текущем состоянии монтирования"""
        status = {
            'mount_points': {},
            'count': len(self.mount_points)
        }
        
        for share_path, mount_point in self.mount_points.items():
            is_mounted = os.path.ismount(str(mount_point))
            status['mount_points'][share_path] = {
                'mount_point': str(mount_point),
                'is_mounted': is_mounted,
                'exists': os.path.exists(str(mount_point))
            }
        return status