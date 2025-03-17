# app/routes.py
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from app.utils.samba_mounter import SambaMounter
from app.utils.file_scanner import FileScanner
from app.utils.exif_parser import ExifParser
from app.models import Database
import logging
import os
import uuid
from bson.objectid import ObjectId

# Инициализация объектов
samba_mounter = SambaMounter()
db = Database()
file_scanner = FileScanner(db)
exif_parser = ExifParser()
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
    
    # Создаем уникальный идентификатор сессии
    session_id = str(uuid.uuid4())
    session['scan_session_id'] = session_id
    
    # Монтируем сетевые ресурсы, если необходимо
    mounted_dirs = []
    try:
        for dir_path in directories:
            if dir_path.startswith('//'):
                # Монтируем Samba-ресурс
                try:
                    mounted_path = samba_mounter.mount_share(dir_path, username, password)
                    mounted_dirs.append(mounted_path)
                except Exception as e:
                    logger.error(f"Ошибка при монтировании {dir_path}: {e}")
                    flash(f'Ошибка при монтировании {dir_path}: {e}', 'danger')
                    return redirect(url_for('index'))
            else:
                mounted_dirs.append(dir_path)
        
        # Создаем новую сессию сканирования
        db_session_id = db.save_scan_session(directories)
        session['db_session_id'] = str(db_session_id)
     
        # Выполняем сканирование директорий
        duplicates = file_scanner.scan_directories(mounted_dirs)
        
        # Обработка найденных дубликатов
        processed_duplicates = []
        has_exif_differences = False
        
        for filename, files in duplicates.items():
            # Добавляем превью и обрабатываем EXIF для каждого файла
            for file in files:
                # Генерируем превью
                file['preview'] = file_scanner.generate_preview(file['path'])
                
                # Проверяем наличие различий в EXIF между дубликатами
                if len(files) > 1:
                    exif_differences = file_scanner.compare_duplicates(files)
                    if exif_differences:
                        has_exif_differences = True
            
            # Добавляем группу в обработанные результаты
            processed_duplicates.append({
                'filename': filename,
                'files': files
            })
        
        # Сохраняем результаты в базу данных
        db.save_duplicates(db_session_id, {filename: files for filename, files in duplicates.items()})
        
        # Передаем результаты на страницу отображения
        return render_template('results.html', 
                              duplicates=processed_duplicates,
                              directories=directories,
                              has_exif_differences=has_exif_differences,
                              session_id=session_id)
                              
    except Exception as e:
        logger.error(f"Ошибка при сканировании: {e}")
        flash(f'Произошла ошибка: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        # Размонтируем все ресурсы
        try:
            samba_mounter.unmount_all()
        except Exception as e:
            logger.error(f"Ошибка при размонтировании ресурсов: {e}")

@app.route('/results/<session_id>')
@app.route('/results/<session_id>')
def view_results(session_id):
    """Просмотр результатов предыдущего сканирования"""
    try:
        # Получаем результаты сканирования из базы данных
        session_info = db.db.scan_sessions.find_one({'_id': ObjectId(session_id)})
        
        if not session_info:
            flash('Сессия не найдена', 'danger')
            return redirect(url_for('index'))
        
        # Получаем группы дубликатов
        duplicate_groups = list(db.db.duplicate_groups.find({'session_id': session_id}))
        
        processed_duplicates = []
        has_exif_differences = False
        
        for group in duplicate_groups:
            files = group['files']
            
            # Проверяем наличие файлов и добавляем превью
            valid_files = []
            for file in files:
                if os.path.exists(file['path']):
                    # Генерируем превью, если его нет
                    if 'preview' not in file or not file['preview']:
                        file['preview'] = file_scanner.generate_preview(file['path'])
                    valid_files.append(file)
            
            # Если есть действительные файлы, добавляем группу
            if valid_files:
                # Проверяем наличие различий в EXIF
                if len(valid_files) > 1:
                    exif_differences = file_scanner.compare_duplicates(valid_files)
                    if exif_differences:
                        has_exif_differences = True
                
                processed_duplicates.append({
                    'filename': group['filename'],
                    'files': valid_files
                })
        
        # Отображаем результаты
        return render_template('results.html', 
                              duplicates=processed_duplicates, 
                              directories=session_info['directories'],
                              has_exif_differences=has_exif_differences,
                              session_id=session_id)
    except Exception as e:
        logger.error(f"Ошибка при загрузке результатов: {e}")
        flash(f'Произошла ошибка: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/delete_files', methods=['POST'])
def delete_files():
    """Удаление выбранных файлов"""
    if request.method == 'POST':
        files_to_delete = request.form.getlist('delete_files')
        session_id = request.form.get('session_id')
        
        if not files_to_delete:
            flash('Не выбрано ни одного файла для удаления', 'warning')
            return redirect(url_for('view_results', session_id=session_id))
        
        deleted_count = 0
        error_count = 0
        
        for file_path in files_to_delete:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    # Обновляем информацию в базе данных
                    db.db.duplicate_groups.update_many(
                        {'files.path': file_path},
                        {'$pull': {'files': {'path': file_path}}}
                    )
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {file_path}: {e}")
                error_count += 1
        
        if deleted_count > 0:
            flash(f'Успешно удалено файлов: {deleted_count}', 'success')
        
        if error_count > 0:
            flash(f'Не удалось удалить файлов: {error_count}', 'danger')
        
        return redirect(url_for('view_results', session_id=session_id))

@app.route('/compare_exif/<group_id>')

def compare_exif(group_id):
    """API для сравнения EXIF-метаданных между файлами одной группы"""
    try:
        session_id = session.get('db_session_id')
        if not session_id:
            return jsonify({'error': 'Сессия не найдена'}), 404
        
        # Получаем группу дубликатов
        group = db.db.duplicate_groups.find_one({
            'session_id': session_id,
            '_id': ObjectId(group_id)
        })
        
        if not group:
            return jsonify({'error': 'Группа не найдена'}), 404
        
        files = group['files']
        
        # Если в группе менее 2 файлов, сравнение не имеет смысла
        if len(files) < 2:
            return jsonify({'error': 'Недостаточно файлов для сравнения'}), 400
        
        # Сравниваем EXIF-метаданные
        exif_differences = file_scanner.compare_duplicates(files)
        
        return jsonify({
            'group_name': group['filename'],
            'files': [{'path': f['path'], 'name': f['name']} for f in files],
            'differences': exif_differences
        })
    except Exception as e:
        logger.error(f"Ошибка при сравнении EXIF: {e}")
        return jsonify({'error': str(e)}), 500