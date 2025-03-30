from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from app.utils.samba_mounter import SambaMounter
from app.utils.file_scanner import FileScanner
from app.utils.exif_parser import ExifParser
from app.models import Database
import logging
import os
import uuid
import datetime  
from bson.objectid import ObjectId

samba_mounter = SambaMounter()
db = Database()
exif_parser = ExifParser()
file_scanner = FileScanner(db)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_directories():
    directories = []
    for i in range(1, 5):
        dir_path = request.form.get(f'directory{i}')
        if dir_path and dir_path.strip():
            directories.append(dir_path.strip())
    
    if not directories:
        flash('Необходимо указать хотя бы одну директорию', 'danger')
        return redirect(url_for('index'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Use only one consistent ID format
    db_session_id = db.save_scan_session(directories)
    session['db_session_id'] = str(db_session_id)
    
    # Сохраняем учетные данные в сессию для последующего использования при удалении
    if username:
        session['scan_username'] = username
    if password:
        session['scan_password'] = password
    
    mounted_dirs = []
    mount_error = False
    
    try:
        for dir_path in directories:
            if dir_path.startswith('//'):
                try:
                    mounted_path = samba_mounter.mount_share(dir_path, username, password)
                    mounted_dirs.append(mounted_path)
                    logger.info(f"Успешно примонтирован {dir_path} к {mounted_path}")
                except Exception as e:
                    logger.error(f"Ошибка при монтировании {dir_path}: {e}")
                    flash(f'Ошибка при монтировании {dir_path}: {e}', 'danger')
                    mount_error = True
                    return redirect(url_for('index'))
            else:
                mounted_dirs.append(dir_path)
        
        # Сохраняем информацию о монтировании в базе данных
        mount_status = samba_mounter.get_mount_status()
        logger.info(f"Состояние монтирования перед сканированием: {mount_status}")
        
        duplicates = file_scanner.scan_directories(mounted_dirs)
        processed_duplicates = []
        
        for group_idx, (filename, files) in enumerate(duplicates.items()):
            exif_differences = {}
            if len(files) > 1:
                exif_differences = file_scanner.compare_duplicates(files)
            
            for file_idx, file in enumerate(files):
                file['preview'] = file_scanner.generate_preview(file['path'])
                file['exif_display'] = {}
                file['exif_id'] = f"exif-{group_idx}-{file_idx}"  
                for key, value in file['exif'].items():
                    display_name = exif_parser.get_exif_display_name(key)
                    file['exif_display'][display_name] = value
            
            processed_duplicates.append({
                'filename': filename,
                'files': files,
                'exif_differences': exif_differences,
                'group_id': group_idx  
            })
        
        db.save_duplicates(db_session_id, {filename: files for filename, files in duplicates.items()})
        
        return render_template('results.html', 
                              duplicates=processed_duplicates,
                              directories=directories,
                              session_id=str(db_session_id))  # Pass MongoDB ObjectId as string
    except Exception as e:
        logger.error(f"Ошибка при сканировании: {e}")
        flash(f'Произошла ошибка: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        # Размонтируем только если была ошибка
        if mount_error:
            try:
                logger.info("Размонтирование ресурсов из-за ошибки")
                samba_mounter.unmount_all()
            except Exception as e:
                logger.error(f"Ошибка при размонтировании ресурсов: {e}")

@app.route('/results/<session_id>')
def view_results(session_id):
    try:
        # Convert string session_id to ObjectId for MongoDB query
        obj_session_id = ObjectId(session_id)
        
        session_info = db.db.scan_sessions.find_one({'_id': obj_session_id})
        if not session_info:
            flash('Сессия не найдена', 'danger')
            return redirect(url_for('index'))
        
        # Use the same session_id format for marked_files collection
        marked_files_doc = db.db.marked_files.find_one({'session_id': session_id})
        marked_files = marked_files_doc.get('files', []) if marked_files_doc else []
        marked_count = len(marked_files)
        
        duplicate_groups = list(db.db.duplicate_groups.find({'session_id': session_id}))
        processed_duplicates = []
        
        for group_idx, group in enumerate(duplicate_groups):
            files = group['files']
            valid_files = []
            
            for file_idx, file in enumerate(files):
                if os.path.exists(file['path']):
                    if 'preview' not in file or not file['preview']:
                        file['preview'] = file_scanner.generate_preview(file['path'])
                    file['exif_display'] = {}
                    file['exif_id'] = f"exif-{group_idx}-{file_idx}"
                    for key, value in file['exif'].items():
                        display_name = exif_parser.get_exif_display_name(key)
                        file['exif_display'][display_name] = value
                    file['marked_for_deletion'] = file['path'] in marked_files
                    valid_files.append(file)
            
            if valid_files:
                exif_differences = {}
                exif_diff_tags = set()
                if len(valid_files) > 1:
                    exif_data = [file['exif'] for file in valid_files]
                    for i in range(len(exif_data)):
                        for j in range(i+1, len(exif_data)):
                            differences = exif_parser.compare_exif(exif_data[i], exif_data[j])
                            for key in differences:
                                exif_diff_tags.add(key)
                
                displayed_diff_tags = [exif_parser.get_exif_display_name(tag) for tag in exif_diff_tags]
                processed_duplicates.append({
                    'filename': group['filename'],
                    'files': valid_files,
                    'exif_differences': displayed_diff_tags,  
                    'group_id': group_idx
                })
        
        return render_template('results.html', 
                              duplicates=processed_duplicates, 
                              directories=session_info['directories'],
                              session_id=session_id,
                              marked_count=marked_count)
    except Exception as e:
        logger.error(f"Ошибка при загрузке результатов: {e}")
        flash(f'Произошла ошибка: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/compare_exif/<group_id>')
def compare_exif(group_id):
    try:
        session_id = session.get('db_session_id')
        if not session_id:
            return jsonify({'error': 'Сессия не найдена'}), 404
        
        group = db.db.duplicate_groups.find_one({
            'session_id': session_id,
            '_id': ObjectId(group_id)
        })
        
        if not group:
            return jsonify({'error': 'Группа не найдена'}), 404
        
        files = group['files']
        if len(files) < 2:
            return jsonify({'error': 'Недостаточно файлов для сравнения'}), 400
        
        exif_differences = file_scanner.compare_duplicates(files)
        human_readable_differences = {}
        for key, diff in exif_differences.items():
            display_key = exif_parser.get_exif_display_name(key)
            human_readable_differences[display_key] = diff
        
        return jsonify({
            'group_name': group['filename'],
            'files': [{'path': f['path'], 'name': f['name']} for f in files],
            'differences': human_readable_differences
        })
    except Exception as e:
        logger.error(f"Ошибка при сравнении EXIF: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mark_for_deletion', methods=['POST'])
def mark_for_deletion():
    if request.method == 'POST':
        marked_files = request.form.getlist('marked_files')
        session_id = request.form.get('session_id')
        
        if not session_id:
            flash('Идентификатор сессии не найден', 'danger')
            return redirect(url_for('index'))
        
        # Make sure we can validate this as an ObjectId
        try:
            obj_id = ObjectId(session_id)
        except:
            flash('Неверный формат идентификатора сессии', 'danger')
            return redirect(url_for('index'))
        
        if not marked_files:
            flash('Не выбрано ни одного файла для удаления', 'warning')
            return redirect(url_for('view_results', session_id=session_id))
        
        result = db.db.marked_files.update_one(
            {'session_id': session_id},
            {'$set': {
                'session_id': session_id,
                'files': marked_files,
                'updated_at': datetime.datetime.utcnow()
            }},
            upsert=True
        )
        
        session['has_marked_files'] = True
        flash(f'Отмечено {len(marked_files)} файлов на удаление', 'success')
        return redirect(url_for('view_results', session_id=session_id))

@app.route('/delete_files', methods=['POST'])
def delete_files():
    if request.method == 'POST':
        session_id = request.form.get('session_id')
        
        if not session_id:
            flash('Идентификатор сессии не найден', 'danger')
            return redirect(url_for('index'))
        
        # Получаем информацию о сессии
        obj_session_id = ObjectId(session_id)
        session_info = db.db.scan_sessions.find_one({'_id': obj_session_id})
        if not session_info:
            flash('Сессия не найдена', 'danger')
            return redirect(url_for('index'))
        
        marked_files_doc = db.db.marked_files.find_one({'session_id': session_id})
        if not marked_files_doc or not marked_files_doc.get('files'):
            flash('Нет файлов, отмеченных на удаление', 'warning')
            return redirect(url_for('view_results', session_id=session_id))
        
        files_to_delete = marked_files_doc.get('files', [])
        deleted_files = []
        error_files = []
        
        # Получаем логин и пароль (из формы подтверждения удаления)
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # Если учетные данные не предоставлены, пробуем взять их из сессии
        if not username and 'scan_username' in session:
            username = session.get('scan_username', '')
            logger.info("Используем имя пользователя из сессии")
        
        if not password and 'scan_password' in session:
            password = session.get('scan_password', '')
            logger.info("Используем пароль из сессии")
            
        logger.info(f"Запрос на удаление {len(files_to_delete)} файлов. Учетные данные: {'Предоставлены' if username else 'Не предоставлены'}")
        
        # Проверяем текущее состояние монтирования
        pre_mount_status = samba_mounter.get_mount_status()
        logger.info(f"Текущее состояние монтирования: {pre_mount_status}")
        
        # Монтируем необходимые Samba-ресурсы перед удалением
        directories = session_info.get('directories', [])
        network_dirs = [d for d in directories if d.startswith('//')]
        
        logger.info(f"Директории: {directories}")
        logger.info(f"Сетевые директории: {network_dirs}")
        
        samba_mount_success = True
        mounted_dirs = []
        
        try:
            # Монтируем все сетевые директории, которые еще не примонтированы
            for dir_path in network_dirs:
                # Проверяем, не примонтирован ли уже
                already_mounted = False
                for share_path in pre_mount_status['mount_points']:
                    if dir_path.lower() == share_path.lower():
                        already_mounted = True
                        mounted_path = pre_mount_status['mount_points'][share_path]['mount_point']
                        mounted_dirs.append(mounted_path)
                        logger.info(f"Ресурс {dir_path} уже примонтирован к {mounted_path}")
                        break
                
                if not already_mounted:
                    try:
                        logger.info(f"Монтирование сетевого пути: {dir_path}")
                        mounted_path = samba_mounter.mount_share(dir_path, username, password)
                        mounted_dirs.append(mounted_path)
                        logger.info(f"Успешно примонтирован {dir_path} к {mounted_path}")
                    except Exception as e:
                        samba_mount_success = False
                        error_msg = str(e)
                        logger.error(f"Ошибка при монтировании {dir_path}: {error_msg}")
                        error_files.append({
                            'path': dir_path,
                            'error': f"Не удалось примонтировать: {error_msg}"
                        })
            
            # Отладочная информация о монтировании
            mount_status = samba_mounter.get_mount_status()
            logger.info(f"Состояние монтирования после подготовки: {mount_status}")
            
            # Применяем маппинг путей к файлам, которые нужно удалить
            mapped_files = files_to_delete.copy()
            if mount_status['count'] > 0:
                # Используем новый метод map_paths для маппинга
                mapped_files = samba_mounter.map_paths(files_to_delete)
                logger.info(f"Маппинг путей для удаления: {len(mapped_files)} файлов")
                
                # Выводим в лог для отладки
                for i, (orig, mapped) in enumerate(zip(files_to_delete, mapped_files)):
                    logger.info(f"Файл {i+1}: {orig} -> {mapped}")
            
            # Проверяем существование файлов перед удалением
            for i, file_path in enumerate(mapped_files):
                original_path = files_to_delete[i]
                exists = os.path.exists(file_path)
                is_file = os.path.isfile(file_path) if exists else False
                is_writable = os.access(file_path, os.W_OK) if exists else False
                logger.info(f"Проверка файла {i+1}: {file_path}, существует: {exists}, файл: {is_file}, доступен для записи: {is_writable}")
            
            # Удаляем файлы
            for i, file_path in enumerate(mapped_files):
                original_path = files_to_delete[i]  # для сохранения в БД используем оригинальный путь
                try:
                    logger.info(f"Проверка существования файла: {file_path}")
                    if os.path.exists(file_path):
                        if os.path.isfile(file_path):
                            file_name = os.path.basename(file_path)
                            file_size = os.path.getsize(file_path)
                            logger.info(f"Удаление файла: {file_path}")
                            
                            # Проверяем права доступа
                            if os.access(file_path, os.W_OK):
                                try:
                                    os.remove(file_path)
                                    deleted_files.append({
                                        'path': original_path,  # показываем пользователю оригинальный путь
                                        'name': file_name,
                                        'size': file_size
                                    })
                                    # Удаляем информацию о файле из группы дубликатов
                                    db.db.duplicate_groups.update_many(
                                        {'session_id': session_id, 'files.path': original_path},
                                        {'$pull': {'files': {'path': original_path}}}
                                    )
                                    logger.info(f"Файл успешно удален: {file_path}")
                                except Exception as rem_err:
                                    logger.error(f"Ошибка при удалении файла: {file_path}: {rem_err}")
                                    error_files.append({
                                        'path': original_path,
                                        'error': f"Ошибка при удалении: {str(rem_err)}"
                                    })
                            else:
                                logger.error(f"Нет прав на запись: {file_path}")
                                error_files.append({
                                    'path': original_path,
                                    'error': "Нет прав на запись к файлу"
                                })
                        else:
                            logger.error(f"Путь существует, но это не файл: {file_path}")
                            error_files.append({
                                'path': original_path,
                                'error': "Путь существует, но это не файл"
                            })
                    else:
                        logger.error(f"Файл не существует: {file_path}")
                        error_files.append({
                            'path': original_path,
                            'error': "Файл не найден"
                        })
                except PermissionError as pe:
                    logger.error(f"Ошибка доступа при удалении файла {file_path}: {pe}")
                    error_files.append({
                        'path': original_path,
                        'error': f"Ошибка доступа: {str(pe)}"
                    })
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла {file_path}: {e}")
                    error_files.append({
                        'path': original_path,
                        'error': str(e)
                    })
            
            # Очищаем список файлов, отмеченных на удаление только если были успешные удаления
            if deleted_files:
                db.db.marked_files.delete_one({'session_id': session_id})
                session.pop('has_marked_files', None)
            
            # Сохраняем результаты удаления в сессию для отображения
            session['deleted_files'] = deleted_files
            session['error_files'] = error_files
            
            logger.info(f"Результаты удаления: успешно удалено {len(deleted_files)}, ошибок {len(error_files)}")
            
            return redirect(url_for('delete_results', session_id=session_id))
        
        except Exception as e:
            import traceback
            logger.error(f"Необработанная ошибка при удалении файлов: {e}")
            logger.error(traceback.format_exc())
            flash(f"Произошла ошибка: {str(e)}", 'danger')
            return redirect(url_for('view_results', session_id=session_id))
        finally:
            # Размонтируем все ресурсы после удаления
            try:
                logger.info("Размонтирование всех ресурсов")
                unmount_status = samba_mounter.unmount_all()
                logger.info(f"Результат размонтирования: {unmount_status}")
            except Exception as e:
                logger.error(f"Ошибка при размонтировании ресурсов: {e}")

@app.route('/delete_results/<session_id>')
def delete_results(session_id):
    deleted_files = session.pop('deleted_files', [])
    error_files = session.pop('error_files', [])
    
    total_deleted = len(deleted_files)
    total_size = sum(file.get('size', 0) for file in deleted_files)
    total_errors = len(error_files)
    
    return render_template('delete_results.html', 
                           session_id=session_id,
                           deleted_files=deleted_files,
                           error_files=error_files,
                           total_deleted=total_deleted,
                           total_size=total_size,
                           total_errors=total_errors)