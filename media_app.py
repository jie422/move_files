from flask import Flask, request, jsonify, render_template
import os
import requests
import json
import datetime
from PIL import Image
import numpy as np
import shutil
import base64
from io import BytesIO
import re

from media_mover import move_files_by_date, clean_empty_folders

app = Flask(__name__)

IMAGE_EXTENSIONS = [
    '.jpg', '.jpeg', '.jfif', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif',
    '.ico', '.svg', '.heic', '.heif', '.tga', '.pcx', '.psd', '.raw',
    '.cr2', '.nef', '.arw', '.dng', '.ai', '.eps'
]

UPLOAD_FOLDER = 'uploads'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    print("pillow-heif not installed, HEIC images may not be supported")

API_KEY = "sk-994395b2efb246e8a5fe66b23c5094ec"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
SIMILARITY_THRESHOLD = 0.8

EXT_TO_MIME = {
    '.jpg': 'jpeg', '.jpeg': 'jpeg', '.jfif': 'jpeg', '.png': 'png', '.gif': 'gif',
    '.bmp': 'bmp', '.dib': 'bmp', '.webp': 'webp', '.tiff': 'tiff', '.tif': 'tiff',
    '.ico': 'x-icon', '.svg': 'svg+xml', '.heic': 'heic', '.heif': 'heif',
    '.tga': 'tga', '.pcx': 'pcx', '.psd': 'photoshop', '.raw': 'raw',
    '.cr2': 'x-canon-cr2', '.nef': 'x-nikon-nef', '.arw': 'x-sony-arw',
    '.dng': 'x-adobe-dng', '.ai': 'ai', '.eps': 'eps'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/media-mover')
def media_mover_page():
    return render_template('media_mover.html')

@app.route('/api/organize', methods=['POST'])
def api_organize():
    data = request.get_json()
    source_path = data.get('source_path')
    destination_path = data.get('destination_path')

    if not source_path or not destination_path:
        return jsonify({'error': '缺少源路径或目标路径'}), 400

    if not os.path.exists(source_path):
        return jsonify({'error': f'源路径不存在: {source_path}'}), 400

    try:
        results = move_files_by_date(source_path, destination_path)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST'])
def api_clean():
    data = request.get_json()
    clean_path = data.get('path')

    if not clean_path:
        return jsonify({'error': '缺少路径'}), 400

    if not os.path.exists(clean_path):
        return jsonify({'error': f'路径不存在: {clean_path}'}), 400

    try:
        removed_folders = clean_empty_folders(clean_path)
        return jsonify({
            'success': True,
            'removed_folders': removed_folders,
            'removed_count': len(removed_folders)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_image_mime_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return EXT_TO_MIME.get(ext, 'jpeg')

def convert_image_to_jpeg(image_path, max_size=800):
    try:
        with Image.open(image_path) as img:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=70, optimize=True, progressive=True)
            return buffer.getvalue()
    except Exception as e:
        print(f"转换图像 {image_path} 时出错: {e}")
        return None

def get_image_info(image_path):
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            headers = {'Authorization': f'Bearer {API_KEY}'}
            response = requests.post(API_URL, files=files, headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"识别图像 {image_path} 时出错: {e}")
        return None

def calculate_similarity(feature1, feature2):
    if not feature1 or not feature2:
        return 0.0
    feature1 = np.array(feature1)
    feature2 = np.array(feature2)
    if len(feature1) != len(feature2):
        return 0.0
    dot_product = np.dot(feature1, feature2)
    norm1 = np.linalg.norm(feature1)
    norm2 = np.linalg.norm(feature2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def get_image_date(image_path):
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if exif_data:
                if 36867 in exif_data:
                    date_str = exif_data[36867]
                    return datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return None

def process_images(directory):
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                image_files.append(os.path.join(root, file))

    image_info = []
    for img_path in image_files:
        info = get_image_info(img_path)
        img_date = get_image_date(img_path)
        if img_date is None:
            img_date = datetime.datetime.fromtimestamp(os.path.getmtime(img_path))
        if info:
            image_info.append({'path': img_path, 'info': info, 'date': img_date})
        else:
            image_info.append({'path': img_path, 'info': None, 'date': img_date})

    similar_groups = []
    processed = set()

    for i, img1 in enumerate(image_info):
        if i in processed:
            continue
        group = [img1]
        processed.add(i)

        for j, img2 in enumerate(image_info):
            if j in processed or i == j:
                continue
            similarity = calculate_similarity(img1['info'].get('features'), img2['info'].get('features'))
            if similarity >= SIMILARITY_THRESHOLD:
                group.append(img2)
                processed.add(j)

        if len(group) > 1:
            similar_groups.append(group)

    for img in image_info:
        date = img['date']
        year = str(date.year)
        month = f"{date.month:02d}"
        year_folder = os.path.join(directory, year)
        if not os.path.exists(year_folder):
            os.makedirs(year_folder)
        month_folder = os.path.join(year_folder, month)
        if not os.path.exists(month_folder):
            os.makedirs(month_folder)
        dest_path = os.path.join(month_folder, os.path.basename(img['path']))
        if not os.path.exists(dest_path):
            shutil.move(img['path'], dest_path)
            print(f"已移动 {os.path.basename(img['path'])} 到 {month_folder}")

    return {'similar_groups': similar_groups, 'all_images': image_info}

@app.route('/scan-local', methods=['GET'])
def scan_local():
    image_files = []
    for root, _, files in os.walk(SCRIPT_DIR):
        for file in files:
            if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                rel_path = os.path.relpath(root, SCRIPT_DIR)
                path_parts = rel_path.split(os.sep)
                should_exclude = False
                for part in path_parts:
                    if part == 'uploads':
                        should_exclude = True
                        break
                    if part.isdigit() and len(part) == 4 and 2000 <= int(part) <= 2100:
                        should_exclude = True
                        break
                    if part.isdigit() and len(part) == 2 and 1 <= int(part) <= 12:
                        should_exclude = True
                        break
                if not should_exclude:
                    file_path = os.path.join(root, file)
                    if os.path.getsize(file_path) >= 10 * 1024:
                        image_files.append({
                            'name': file,
                            'path': file_path,
                            'folder': rel_path if rel_path != '.' else '当前目录'
                        })
                        if len(image_files) >= 30:
                            break
        if len(image_files) >= 30:
            break

    if not image_files:
        return jsonify({'error': 'No images found in script directory', 'images': []})

    images_data = []
    for img in image_files:
        try:
            img_data = convert_image_to_jpeg(img['path'])
            if img_data is None:
                with open(img['path'], 'rb') as f:
                    img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            file_mtime = os.path.getmtime(img['path'])
            file_date = datetime.datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d')
            images_data.append({
                'name': img['name'],
                'path': f"data:image/jpeg;base64,{img_base64}",
                'date': file_date,
                'fullPath': img['path'],
                'folder': img['folder']
            })
        except Exception as e:
            print(f"读取图像 {img['path']} 时出错: {e}")

    return jsonify({'images': images_data, 'total': len(images_data)})

@app.route('/get-image-folders', methods=['GET'])
def get_image_folders():
    folders = set()
    for root, _, files in os.walk(SCRIPT_DIR):
        has_images = False
        for file in files:
            if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                has_images = True
                break
        if has_images:
            has_large_images = False
            for file in files:
                if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    if os.path.getsize(file_path) >= 10 * 1024:
                        has_large_images = True
                        break
            if has_large_images:
                rel_path = os.path.relpath(root, SCRIPT_DIR)
                path_parts = rel_path.split(os.sep)
                should_exclude = False
                for part in path_parts:
                    if part == 'uploads':
                        should_exclude = True
                        break
                    if part.isdigit() and len(part) == 4 and 2000 <= int(part) <= 2100:
                        should_exclude = True
                        break
                    if part.isdigit() and len(part) == 2 and 1 <= int(part) <= 12:
                        should_exclude = True
                        break
                if not should_exclude:
                    folders.add(rel_path if rel_path != '.' else '当前目录')

    folder_list = sorted(list(folders))
    return jsonify({'folders': folder_list, 'total': len(folder_list)})

@app.route('/process-selected', methods=['POST'])
def process_selected():
    data = request.get_json()
    selected_images = data.get('images', [])
    if not selected_images:
        return jsonify({'error': 'No images selected'}), 400

    moved_images = []
    for img_path in selected_images:
        try:
            img_date = get_image_date(img_path)
            if img_date is None:
                img_date = datetime.datetime.fromtimestamp(os.path.getmtime(img_path))
            year = str(img_date.year)
            month = f"{img_date.month:02d}"
            year_folder = os.path.join(SCRIPT_DIR, year)
            if not os.path.exists(year_folder):
                os.makedirs(year_folder)
            month_folder = os.path.join(year_folder, month)
            if not os.path.exists(month_folder):
                os.makedirs(month_folder)

            base_name = os.path.basename(img_path)
            name_without_ext = os.path.splitext(base_name)[0]
            date_pattern = re.compile(r'^\d{8}_|^\d{4}-\d{2}-\d{2}_')
            is_date_named = bool(date_pattern.match(name_without_ext))

            ext = os.path.splitext(img_path)[1]
            if is_date_named:
                new_filename = base_name
            else:
                if img_date:
                    new_filename = f"{img_date.strftime('%Y%m%d_%H%M%S')}{ext}"
                else:
                    current_time = datetime.datetime.now()
                    new_filename = f"{current_time.strftime('%Y%m%d_%H%M%S')}{ext}"

            dest_path = os.path.join(month_folder, new_filename)
            counter = 1
            while os.path.exists(dest_path):
                if is_date_named:
                    name_parts = name_without_ext.split('_')
                    if name_parts[-1].isdigit():
                        name_parts[-1] = str(counter)
                    else:
                        name_parts.append(str(counter))
                    new_filename = f"{'_'.join(name_parts)}{ext}"
                else:
                    if img_date:
                        new_filename = f"{img_date.strftime('%Y%m%d_%H%M%S')}_{counter}{ext}"
                    else:
                        new_filename = f"{current_time.strftime('%Y%m%d_%H%M%S')}_{counter}{ext}"
                dest_path = os.path.join(month_folder, new_filename)
                counter += 1

            shutil.move(img_path, dest_path)
            moved_images.append({'name': os.path.basename(img_path), 'from': img_path, 'to': dest_path})
            print(f"已移动 {os.path.basename(img_path)} 到 {dest_path}")

            original_folder = os.path.dirname(img_path)
            if original_folder != SCRIPT_DIR:
                try:
                    if os.path.exists(original_folder) and not os.listdir(original_folder):
                        os.rmdir(original_folder)
                        print(f"删除空文件夹: {original_folder}")
                except Exception as e:
                    print(f"删除空文件夹 {original_folder} 时出错: {e}")
        except Exception as e:
            print(f"处理图像 {img_path} 时出错: {e}")

    return jsonify({'success': True, 'moved': moved_images, 'total': len(moved_images)})

@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    saved_files = []
    files = files[:30]

    for file in files:
        if file and any(file.filename.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size >= 10 * 1024:
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                saved_files.append(filepath)
            else:
                print(f"跳过小文件: {file.filename} ({file_size} 字节)")

    if not saved_files:
        return jsonify({'error': 'No valid image files provided'}), 400

    image_info = []
    for img_path in saved_files:
        info = get_image_info(img_path)
        img_date = get_image_date(img_path)
        if img_date is None:
            img_date = datetime.datetime.fromtimestamp(os.path.getmtime(img_path))
        if info:
            image_info.append({'path': img_path, 'info': info, 'date': img_date})
        else:
            image_info.append({'path': img_path, 'info': None, 'date': img_date})

    similar_groups = []
    processed = set()

    for i, img1 in enumerate(image_info):
        if i in processed:
            continue
        group = [img1]
        processed.add(i)

        for j, img2 in enumerate(image_info):
            if j in processed or i == j:
                continue
            similarity = calculate_similarity(img1['info'].get('features'), img2['info'].get('features'))
            if similarity >= SIMILARITY_THRESHOLD:
                group.append(img2)
                processed.add(j)

        if len(group) > 1:
            similar_groups.append(group)

    front_end_results = {'similarGroups': [], 'allImages': []}
    limited_groups = similar_groups[:30]
    for group in limited_groups:
        group_images = []
        limited_group_images = group[:30]
        for img in limited_group_images:
            with open(img['path'], 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            group_images.append({
                'name': os.path.basename(img['path']),
                'path': f"data:image/{get_image_mime_type(img['path'])};base64,{img_base64}",
                'date': img['date'].strftime('%Y-%m-%d')
            })
        front_end_results['similarGroups'].append({'images': group_images, 'similarity': 0.85})

    limited_all_images = image_info[:30]
    for img in limited_all_images:
        with open(img['path'], 'rb') as f:
            img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
        front_end_results['allImages'].append({
            'name': os.path.basename(img['path']),
            'path': f"data:image/{get_image_mime_type(img['path'])};base64,{img_base64}",
            'date': img['date'].strftime('%Y-%m-%d')
        })

    front_end_results['total'] = len(front_end_results['allImages'])
    return jsonify(front_end_results)

@app.route('/process-folder', methods=['POST'])
def process_folder():
    data = request.get_json()
    folder_path = data.get('folderPath')

    if not folder_path or not os.path.exists(folder_path):
        return jsonify({'error': 'Invalid folder path'}), 400

    results = process_images(folder_path)
    front_end_results = {'similarGroups': [], 'allImages': []}

    limited_groups = results['similar_groups'][:30]
    for group in limited_groups:
        group_images = []
        limited_group_images = group[:30]
        for img in limited_group_images:
            with open(img['path'], 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            group_images.append({
                'name': os.path.basename(img['path']),
                'path': f"data:image/{get_image_mime_type(img['path'])};base64,{img_base64}",
                'date': img['date'].strftime('%Y-%m-%d')
            })
        front_end_results['similarGroups'].append({'images': group_images, 'similarity': 0.85})

    limited_all_images = results['all_images'][:30]
    for img in limited_all_images:
        with open(img['path'], 'rb') as f:
            img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
        front_end_results['allImages'].append({
            'name': os.path.basename(img['path']),
            'path': f"data:image/{get_image_mime_type(img['path'])};base64,{img_base64}",
            'date': img['date'].strftime('%Y-%m-%d')
        })

    return jsonify(front_end_results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
