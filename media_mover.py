import os
import shutil
from datetime import datetime
from pathlib import Path

IMAGE_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.heic',
    '.raw', '.cr2', '.nef', '.orf', '.arw'
]

VIDEO_EXTENSIONS = [
    '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.m4v', '.webm', '3gp', '.mpg', '.mpeg', '.vob', '.ts'
]

def get_file_date(file_path):
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp)

def move_files_by_date(source_path, destination_path, progress_callback=None):
    results = {
        'photos': {'moved': 0, 'failed': 0, 'files': []},
        'videos': {'moved': 0, 'failed': 0, 'files': []},
        'total_moved': 0,
        'total_failed': 0
    }

    source_path = Path(source_path)
    destination_path = Path(destination_path)

    if not source_path.exists():
        return {'error': f'源路径不存在: {source_path}'}

    destination_path.mkdir(parents=True, exist_ok=True)
    (destination_path / 'photos').mkdir(parents=True, exist_ok=True)
    (destination_path / 'videos').mkdir(parents=True, exist_ok=True)

    all_files = list(source_path.rglob('*'))
    total_files = len([f for f in all_files if f.is_file()])
    processed = 0

    for file_path in source_path.rglob('*'):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()

        if ext in IMAGE_EXTENSIONS:
            folder_type = 'photos'
            file_date = get_file_date(file_path)
            year = file_date.strftime('%Y')
            month = file_date.strftime('%m')

            date_folder = destination_path / 'photos' / year / month
            date_folder.mkdir(parents=True, exist_ok=True)

            new_file_path = date_folder / file_path.name
            counter = 1
            while new_file_path.exists():
                stem = file_path.stem
                new_file_path = date_folder / f"{stem}_{counter}{file_path.suffix}"
                counter += 1

            try:
                shutil.move(str(file_path), str(new_file_path))
                results['photos']['moved'] += 1
                results['photos']['files'].append({
                    'original': str(file_path),
                    'new': str(new_file_path),
                    'date': f"{year}/{month}"
                })
                results['total_moved'] += 1
            except Exception as e:
                results['photos']['failed'] += 1
                results['total_failed'] += 1

        elif ext in VIDEO_EXTENSIONS:
            folder_type = 'videos'
            file_date = get_file_date(file_path)
            year = file_date.strftime('%Y')
            month = file_date.strftime('%m')

            date_folder = destination_path / 'videos' / year / month
            date_folder.mkdir(parents=True, exist_ok=True)

            new_file_path = date_folder / file_path.name
            counter = 1
            while new_file_path.exists():
                stem = file_path.stem
                new_file_path = date_folder / f"{stem}_{counter}{file_path.suffix}"
                counter += 1

            try:
                shutil.move(str(file_path), str(new_file_path))
                results['videos']['moved'] += 1
                results['videos']['files'].append({
                    'original': str(file_path),
                    'new': str(new_file_path),
                    'date': f"{year}/{month}"
                })
                results['total_moved'] += 1
            except Exception as e:
                results['videos']['failed'] += 1
                results['total_failed'] += 1

        processed += 1
        if progress_callback:
            progress_callback(processed, total_files)

    return results

def clean_empty_folders(path):
    removed_folders = []
    path = Path(path)

    for folder in sorted(path.rglob('*'), key=lambda x: -len(x.parts)):
        if folder.is_dir() and not any(folder.iterdir()):
            try:
                folder.rmdir()
                removed_folders.append(str(folder))
            except Exception:
                pass

    return removed_folders
