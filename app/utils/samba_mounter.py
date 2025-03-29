# app/utils/samba_mounter.py
import os
import subprocess
from pathlib import Path
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
            return str(mount_point)
        mount_options = ['-o', 'ro']  
        if username and password:
            mount_options.extend(['-o', f'username={username},password={password}'])
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
        for share_path in list(self.mount_points.keys()):
            self.unmount_share(share_path)