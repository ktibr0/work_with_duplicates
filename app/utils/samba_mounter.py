# app/utils/samba_mounter.py
import os
import subprocess
from pathlib import Path

class SambaMounter:
    """Класс для монтирования Samba-ресурсов"""
    
    def __init__(self, mount_base_dir='/mnt/samba'):
        self.mount_base_dir = Path(mount_base_dir)
        self.mount_points = {}
        
        # Создаем базовую директорию для монтирования
        os.makedirs(self.mount_base_dir, exist_ok=True)
    
    def mount_share(self, share_path, username=None, password=None):
        """
        Монтирует сетевой ресурс Samba
        
        Args:
            share_path (str): Путь к ресурсу в формате //server/share
            username (str, optional): Имя пользователя
            password (str, optional): Пароль
            
        Returns:
            str: Путь к локальному каталогу монтирования
        """
        # Создаем уникальное имя для точки монтирования
        share_name = share_path.replace('/', '_').replace('\\', '_').strip('_')
        mount_point = self.mount_base_dir / share_name
        
        # Создаем директорию для монтирования
        os.makedirs(mount_point, exist_ok=True)
        
        # Проверяем, не смонтирован ли уже этот ресурс
        if share_path in self.mount_points:
            return str(mount_point)
        
        # Формируем команду монтирования
        mount_options = ['-o', 'ro']  # Только для чтения
        if username and password:
            mount_options.extend(['-o', f'username={username},password={password}'])
            
        # Выполняем монтирование
        try:
            subprocess.run(
                ['mount', '-t', 'cifs', share_path, str(mount_point)] + mount_options,
                check=True
            )
            self.mount_points[share_path] = mount_point
            return str(mount_point)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Ошибка при монтировании {share_path}: {e}")
    
    def unmount_share(self, share_path):
        """
        Размонтирует сетевой ресурс
        
        Args:
            share_path (str): Путь к ресурсу, который был смонтирован
            
        Returns:
            bool: True в случае успеха
        """
        if share_path not in self.mount_points:
            return False
            
        mount_point = self.mount_points[share_path]
        
        try:
            subprocess.run(['umount', str(mount_point)], check=True)
            self.mount_points.pop(share_path)
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Ошибка при размонтировании {share_path}: {e}")
    
    def unmount_all(self):
        """Размонтирует все смонтированные ресурсы"""
        for share_path in list(self.mount_points.keys()):
            self.unmount_share(share_path)