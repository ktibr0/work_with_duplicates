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
    session_id = str(uuid.uuid4())
    session['scan_session_id'] = session_id
    mounted_dirs = []
    try:
        for dir_path in directories:
            if dir_path.startswith('//'):
                try:
                    mounted_path = samba_mounter.mount_share(dir_path, username, password)
                    mounted_dirs.append(mounted_path)
                except Exception as e:
                    logger.error(f"Ошибка при монтировании {dir_path}: {e}")
                    flash(f'Ошибка при монтировании {dir_path}: {e}', 'danger')
                    return redirect(url_for('index'))
            else:
                mounted_dirs.append(dir_path)
        db_session_id = db.save_scan_session(directories)
        session['db_session_id'] = str(db_session_id)
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
                              session_id=session_id)
    except Exception as e:
        logger.error(f"Ошибка при сканировании: {e}")
        flash(f'Произошла ошибка: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        try:
            samba_mounter.unmount_all()
        except Exception as e:
            logger.error(f"Ошибка при размонтировании ресурсов: {e}")
@app.route('/results/<session_id>')
def view_results(session_id):
    try:
        session_info = db.db.scan_sessions.find_one({'_id': ObjectId(session_id)})
        if not session_info:
            flash('Сессия не найдена', 'danger')
            return redirect(url_for('index'))
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
        session_id = str(request.form.get('session_id'))
        if not session_id:
            flash('Идентификатор сессии не найден', 'danger')
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
        marked_files_doc = db.db.marked_files.find_one({'session_id': session_id})
        if not marked_files_doc or not marked_files_doc.get('files'):
            flash('Нет файлов, отмеченных на удаление', 'warning')
            return redirect(url_for('view_results', session_id=session_id))
        files_to_delete = marked_files_doc.get('files', [])
        deleted_count = 0
        error_count = 0
        for file_path in files_to_delete:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    db.db.duplicate_groups.update_many(
                        {'session_id': session_id, 'files.path': file_path},
                        {'$pull': {'files': {'path': file_path}}}
                    )
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {file_path}: {e}")
                error_count += 1
        db.db.marked_files.delete_one({'session_id': session_id})
        session.pop('has_marked_files', None)
        if deleted_count > 0:
            flash(f'Успешно удалено файлов: {deleted_count}', 'success')
        if error_count > 0:
            flash(f'Не удалось удалить файлов: {error_count}', 'danger')
        return redirect(url_for('view_results', session_id=session_id))        