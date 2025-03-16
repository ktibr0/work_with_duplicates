# app/routes.py
from flask import render_template, request, redirect, url_for, flash, session
from app import app
from app.utils.samba_mounter import SambaMounter
from app.utils.file_scanner import FileScanner
from app.models import Database
import logging

# Инициализация объектов
samba_mounter = SambaMounter()
db = Database()
file_scanner = FileScanner(db)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Главная страница с формой выбора директорий"""
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_directories():
    """Обработка запроса на сканирование директорий"""
    # Получаем введенные директории
    directories = []
    for i in range(1, 5):
        dir_path = request.form.get(f'directory{i}')
        if dir_path and dir_path.strip():
            directories.append(dir_path.strip())
    
    if not directories:
        flash('Необходимо указать хотя бы одну директорию', 'danger')
        return redirect(url_for('index'))
    
    # Получаем учетные данные Samba, если указаны
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Монтируем сетевые ресурсы, если необходимо
    mounted_dirs = []
    try:
        for dir_path in directories:
            if dir_path.startswith('//'):
                # Монтируем Samba-ресурс
                mounted_path = samba_mounter.mount_share(dir_path, username, password)
                mounted_dirs.append(mounted_path)
            else:
                mounted_dirs.append(dir_path)
        
        # Создаем новую сессию сканирования
        session_id = db.save_scan_session(directories)
        
        # Сохраняем ID сессии в сессии пользователя
        session['scan_session_id'] = session_id
        
        # Выполняем сканирование директорий
        duplicates = file_scanner.scan_directories(mounted_dirs)
        
        # Добавляем превью к найденным файлам
        for filename, files in duplicates.items():
            for file in files:
                file['preview'] = file_scanner.generate_preview(file['path'])
        
        # Сохраняем результаты в базу данных
        db.save_duplicates(session_id, duplicates)
        
        # Передаем результаты на страницу отображения
        return render_template('results.html', 
                             duplicates=duplicates.items(), 
                             directories=directories)
                             
    except Exception as e:
        logger.error(f"Ошибка при сканировании: {e}")
        flash(f'Произошла ошибка: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        # Размонтируем все ресурсы
        samba_mounter.unmount_all()

@app.route('/results/<session_id>')
def view_results(session_id):
    """Просмотр результатов предыдущего сканирования"""
    try:
        # Получаем результаты сканирования из базы данных
        duplicates = db.get_session_duplicates(session_id)
        session_info = db.db.scan_sessions.find_one({'_id': session_id})
        
        if not session_info:
            flash('Сессия не найдена', 'danger')
            return redirect(url_for('index'))
            
        # Отображаем результаты
        return render_template('results.html', 
                             duplicates=duplicates, 
                             directories=session_info['directories'])
    except Exception as e:
        logger.error(f"Ошибка при загрузке результатов: {e}")
        flash(f'Произошла ошибка: {e}', 'danger')
        return redirect(url_for('index'))