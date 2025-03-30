# PhotoDublV.3

## 🇷🇺 Русская версия

### О проекте

PhotoDublV.3 - это веб-приложение для поиска и удаления дубликатов фотографий, которое позволяет сканировать локальные и сетевые директории на наличие идентичных изображений. Приложение анализирует EXIF-данные, сравнивает метаданные и помогает принять решение о том, какие именно дубликаты стоит удалить.

### Основные возможности

- Сканирование до 5 локальных и сетевых (SMB/CIFS) директорий одновременно
- Автоматическое монтирование сетевых ресурсов
- Поиск идентичных фотографий на основе имени файла
- Анализ и сравнение EXIF-метаданных
- Подсветка различий в метаданных для принятия решения
- Возможность отметить файлы для удаления
- Безопасное удаление отмеченных дубликатов
- Детальный отчет о результатах удаления

### Технологии

- Python 3.x
- Flask
- MongoDB
- Pillow (для обработки изображений)
- Bootstrap 5 (для интерфейса)
- jQuery
- CIFS/SMB для работы с сетевыми ресурсами

### Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ktibr0/work_with_duplicates
cd work_with_duplicates
```

2. Перейдите в папку docker:
```bash
cd docker
```

3. Запустите контейнер:
```bash
 docker compose up -d
```

4. Откройте веб-браузер и перейдите по адресу http://localhost:5000

### Использование

1. На главной странице укажите до 5 директорий для сканирования
2. Если требуется, введите учетные данные для доступа к сетевым ресурсам
3. Нажмите "Сканировать"
4. После завершения сканирования просмотрите найденные группы дубликатов
5. Отметьте файлы, которые хотите удалить (в каждой группе должен остаться хотя бы один файл)
6. Нажмите "Отметить выбранные на удаление"
7. Подтвердите удаление, нажав "Удалить отмеченные файлы"
8. Просмотрите результаты удаления

### Требования к системе

- Python 3.6 или выше
- MongoDB
- Система с поддержкой монтирования CIFS/SMB ресурсов (Linux/Mac/Windows с WSL)
- Права на монтирование и размонтирование сетевых ресурсов
- Для работы с сетевыми ресурсами могут потребоваться дополнительные пакеты (cifs-utils в Linux)

---

## 🇬🇧 English Version

### About the Project

PhotoDublV.3 is a web application for finding and deleting duplicate photos that can scan local and network directories for identical images. The application analyzes EXIF data, compares metadata, and helps you decide which duplicates to delete.

### Key Features

- Scan up to 5 local and network (SMB/CIFS) directories simultaneously
- Automatic mounting of network resources
- Find identical photos based on filename
- Analyze and compare EXIF metadata
- Highlight differences in metadata to help decision making
- Mark files for deletion
- Safely delete marked duplicates
- Detailed deletion results report

### Technologies

- Python 3.x
- Flask
- MongoDB
- Pillow (for image processing)
- Bootstrap 5 (for UI)
- jQuery
- CIFS/SMB for network resource handling

### Installation and Running

1. Clone the repository:
```bash
git clone https://github.com/ktibr0/work_with_duplicates
cd work_with_duplicates
```

2. Go to folder docker:
```bash
cd docker
```

3. Run container:
```bash
docker compose up -d
```

4. Open a web browser and go to http://localhost:5000

### Usage

1. On the main page, specify up to 5 directories to scan
2. If required, enter credentials for accessing network resources
3. Click "Scan"
4. After scanning is complete, view the found duplicate groups
5. Mark files you want to delete (at least one file must remain in each group)
6. Click "Mark selected for deletion"
7. Confirm deletion by clicking "Delete marked files"
8. View deletion results

### System Requirements

- Python 3.6 or higher
- MongoDB
- System with CIFS/SMB mounting support (Linux/Mac/Windows with WSL)
- Permissions to mount and unmount network resources
- Additional packages may be required for network resources (cifs-utils on Linux) 
