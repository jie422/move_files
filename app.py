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

# 尝试导入pillow-heif来处理HEIC格式
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    print("pillow-heif not installed, HEIC images may not be supported")

app = Flask(__name__)

# 千文图像识别API配置
API_KEY = ""  # 请替换为真实的API密钥
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 假设的API地址

# 配置参数
SIMILARITY_THRESHOLD = 0.8  # 相似度阈值
IMAGE_EXTENSIONS = [
    '.jpg', '.jpeg', '.jfif',  # JPEG格式
    '.png',  # PNG格式
    '.gif',  # GIF格式
    '.bmp', '.dib',  # BMP格式
    '.webp',  # WebP格式
    '.tiff', '.tif',  # TIFF格式
    '.ico',  # 图标格式
    '.svg',  # SVG矢量图形
    '.heic', '.heif',  # HEIF格式
    '.tga',  # TGA格式
    '.pcx',  # PCX格式
    '.psd',  # Photoshop格式
    '.raw',  # RAW格式
    '.cr2', '.nef', '.arw', '.dng',  # 相机RAW格式
    '.ai', '.eps',  # 矢量图形格式
]
UPLOAD_FOLDER = 'uploads'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # 获取脚本所在目录
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 图像扩展名到MIME类型的映射
EXT_TO_MIME = {
    '.jpg': 'jpeg',
    '.jpeg': 'jpeg',
    '.jfif': 'jpeg',
    '.png': 'png',
    '.gif': 'gif',
    '.bmp': 'bmp',
    '.dib': 'bmp',
    '.webp': 'webp',
    '.tiff': 'tiff',
    '.tif': 'tiff',
    '.ico': 'x-icon',
    '.svg': 'svg+xml',
    '.heic': 'heic',
    '.heif': 'heif',
    '.tga': 'tga',
    '.pcx': 'pcx',
    '.psd': 'photoshop',
    '.raw': 'raw',
    '.cr2': 'x-canon-cr2',
    '.nef': 'x-nikon-nef',
    '.arw': 'x-sony-arw',
    '.dng': 'x-adobe-dng',
    '.ai': 'ai',
    '.eps': 'eps'
}

def get_image_mime_type(file_path):
    """根据文件扩展名获取MIME类型"""
    ext = os.path.splitext(file_path)[1].lower()
    return EXT_TO_MIME.get(ext, 'jpeg')

def convert_image_to_jpeg(image_path, max_size=800):
    """将图像转换为JPEG格式的base64编码，并进行压缩"""
    try:
        with Image.open(image_path) as img:
            # 调整图像尺寸
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            
            # 如果图像有透明通道，转换为RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 保存到BytesIO，使用较低的质量进行压缩
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=70, optimize=True, progressive=True)
            return buffer.getvalue()
    except Exception as e:
        print(f"转换图像 {image_path} 时出错: {e}")
        return None

def get_image_info(image_path):
    """调用千文API获取图像信息"""
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
    """计算两个特征向量的相似度"""
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
    """获取图像拍摄日期"""
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
    """处理目录中的所有图像"""
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
            # 如果没有拍摄日期，使用文件修改时间
            img_date = datetime.datetime.fromtimestamp(os.path.getmtime(img_path))
        if info:
            image_info.append({
                'path': img_path,
                'info': info,
                'date': img_date
            })
        else:
            # 即使API调用失败，也要添加到列表中
            image_info.append({
                'path': img_path,
                'info': None,
                'date': img_date
            })
    
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
            
            similarity = calculate_similarity(
                img1['info'].get('features'),
                img2['info'].get('features')
            )
            
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
    
    return {
        'similar_groups': similar_groups,
        'all_images': image_info
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan-local', methods=['GET'])
def scan_local():
    """扫描脚本所在目录的图像文件"""
    # 扫描脚本所在目录
    image_files = []
    for root, _, files in os.walk(SCRIPT_DIR):
        for file in files:
            if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                # 获取相对于脚本目录的路径
                rel_path = os.path.relpath(root, SCRIPT_DIR)
                path_parts = rel_path.split(os.sep)
                
                # 排除uploads文件夹和已经是年月分类的文件夹（如2023、2024等）
                should_exclude = False
                for part in path_parts:
                    if part == 'uploads':
                        should_exclude = True
                        break
                    # 检查是否是年份文件夹（4位数字）
                    if part.isdigit() and len(part) == 4 and 2000 <= int(part) <= 2100:
                        should_exclude = True
                        break
                    # 检查是否是月份文件夹（2位数字，如01、02等）
                    if part.isdigit() and len(part) == 2 and 1 <= int(part) <= 12:
                        should_exclude = True
                        break
                
                if not should_exclude:
                    # 检查文件大小，过滤掉小于10KB的文件
                    file_path = os.path.join(root, file)
                    if os.path.getsize(file_path) >= 10 * 1024:  # 10KB = 10240字节
                        image_files.append({
                            'name': file,
                            'path': file_path,
                            'folder': rel_path if rel_path != '.' else '当前目录'
                        })
                        # 限制最多30个文件
                        if len(image_files) >= 30:
                            break
        if len(image_files) >= 30:
            break
    
    if not image_files:
        return jsonify({
            'error': 'No images found in script directory',
            'images': []
        })
    
    # 读取所有图像并转换为base64
    images_data = []
    for img in image_files:
        try:
            # 将图像转换为JPEG格式（确保浏览器支持）
            img_data = convert_image_to_jpeg(img['path'])
            if img_data is None:
                # 如果转换失败，尝试直接读取
                with open(img['path'], 'rb') as f:
                    img_data = f.read()
            
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # 获取文件修改时间作为日期
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
    
    return jsonify({
        'images': images_data,
        'total': len(images_data)
    })

@app.route('/get-image-folders', methods=['GET'])
def get_image_folders():
    """获取所有包含图片的文件夹"""
    folders = set()
    
    # 扫描脚本所在目录
    for root, _, files in os.walk(SCRIPT_DIR):
        has_images = False
        for file in files:
            if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                has_images = True
                break
        
        if has_images:
            # 检查是否有大于10KB的图像
            has_large_images = False
            for file in files:
                if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    if os.path.getsize(file_path) >= 10 * 1024:  # 10KB = 10240字节
                        has_large_images = True
                        break
            
            if has_large_images:
                # 获取相对于脚本目录的路径
                rel_path = os.path.relpath(root, SCRIPT_DIR)
                path_parts = rel_path.split(os.sep)
                
                # 排除uploads文件夹和已经是年月分类的文件夹（如2023、2024等）
                should_exclude = False
                for part in path_parts:
                    if part == 'uploads':
                        should_exclude = True
                        break
                    # 检查是否是年份文件夹（4位数字）
                    if part.isdigit() and len(part) == 4 and 2000 <= int(part) <= 2100:
                        should_exclude = True
                        break
                    # 检查是否是月份文件夹（2位数字，如01、02等）
                    if part.isdigit() and len(part) == 2 and 1 <= int(part) <= 12:
                        should_exclude = True
                        break
                
                if not should_exclude:
                    folders.add(rel_path if rel_path != '.' else '当前目录')
    
    # 转换为列表并排序
    folder_list = sorted(list(folders))
    
    return jsonify({
        'folders': folder_list,
        'total': len(folder_list)
    })

@app.route('/process-selected', methods=['POST'])
def process_selected():
    """处理选中的图像，按年月分类移动"""
    data = request.get_json()
    selected_images = data.get('images', [])
    
    if not selected_images:
        return jsonify({'error': 'No images selected'}), 400
    
    moved_images = []
    
    for img_path in selected_images:
        try:
            # 获取图像日期
            img_date = get_image_date(img_path)
            if img_date is None:
                # 如果没有拍摄日期，使用文件修改时间
                img_date = datetime.datetime.fromtimestamp(os.path.getmtime(img_path))
            year = str(img_date.year)
            month = f"{img_date.month:02d}"
            
            # 创建年月文件夹
            year_folder = os.path.join(SCRIPT_DIR, year)
            if not os.path.exists(year_folder):
                os.makedirs(year_folder)
            
            month_folder = os.path.join(year_folder, month)
            if not os.path.exists(month_folder):
                os.makedirs(month_folder)
            
            # 检查文件名称是否已经是年月日格式 (YYYYMMDD_*) 或 (YYYY-MM-DD_*)
            base_name = os.path.basename(img_path)
            name_without_ext = os.path.splitext(base_name)[0]
            
            # 检查是否已经是年月日格式
            # 匹配 YYYYMMDD_* 或 YYYY-MM-DD_* 格式
            date_pattern = re.compile(r'^\d{8}_|^\d{4}-\d{2}-\d{2}_')
            is_date_named = bool(date_pattern.match(name_without_ext))
            
            # 移动图像并根据需要重命名
            ext = os.path.splitext(img_path)[1]  # 保留文件扩展名
            if is_date_named:
                # 如果已经是年月日格式，保持原文件名
                new_filename = base_name
            else:
                # 如果不是年月日格式，按照日期重命名
                if img_date:
                    # 使用拍摄日期重命名
                    new_filename = f"{img_date.strftime('%Y%m%d_%H%M%S')}{ext}"
                else:
                    # 如果获取不到拍摄日期，使用当前时间
                    current_time = datetime.datetime.now()
                    new_filename = f"{current_time.strftime('%Y%m%d_%H%M%S')}{ext}"
            
            dest_path = os.path.join(month_folder, new_filename)
            
            # 处理文件名冲突
            counter = 1
            while os.path.exists(dest_path):
                if is_date_named:
                    # 如果已经是日期格式，添加计数器
                    name_parts = name_without_ext.split('_')
                    if name_parts[-1].isdigit():
                        # 如果最后一部分是数字，替换它
                        name_parts[-1] = str(counter)
                    else:
                        # 否则添加计数器
                        name_parts.append(str(counter))
                    new_filename = f"{'_'.join(name_parts)}{ext}"
                else:
                    # 按照之前的逻辑添加计数器
                    if img_date:
                        new_filename = f"{img_date.strftime('%Y%m%d_%H%M%S')}_{counter}{ext}"
                    else:
                        new_filename = f"{current_time.strftime('%Y%m%d_%H%M%S')}_{counter}{ext}"
                dest_path = os.path.join(month_folder, new_filename)
                counter += 1
            
            shutil.move(img_path, dest_path)
            moved_images.append({
                'name': os.path.basename(img_path),
                'from': img_path,
                'to': dest_path
            })
            print(f"已移动 {os.path.basename(img_path)} 到 {dest_path}")
            
            # 检查原文件夹是否为空，如果为空则删除
            original_folder = os.path.dirname(img_path)
            if original_folder != SCRIPT_DIR:  # 不删除脚本根目录
                try:
                    # 检查文件夹是否存在且为空
                    if os.path.exists(original_folder) and not os.listdir(original_folder):
                        os.rmdir(original_folder)
                        print(f"删除空文件夹: {original_folder}")
                except Exception as e:
                    print(f"删除空文件夹 {original_folder} 时出错: {e}")
        except Exception as e:
            print(f"处理图像 {img_path} 时出错: {e}")
    
    return jsonify({
        'success': True,
        'moved': moved_images,
        'total': len(moved_images)
    })

@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    saved_files = []
    
    # 限制最多处理30个文件
    files = files[:30]
    
    for file in files:
        if file and any(file.filename.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
            # 检查文件大小，过滤掉小于10KB的文件
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size >= 10 * 1024:  # 10KB = 10240字节
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                saved_files.append(filepath)
            else:
                print(f"跳过小文件: {file.filename} ({file_size} 字节)")
    
    if not saved_files:
        return jsonify({'error': 'No valid image files provided'}), 400
    
    # 处理上传的文件，只处理当前上传的文件
    image_info = []
    for img_path in saved_files:
        info = get_image_info(img_path)
        img_date = get_image_date(img_path)
        if img_date is None:
            # 如果没有拍摄日期，使用文件修改时间
            img_date = datetime.datetime.fromtimestamp(os.path.getmtime(img_path))
        if info:
            image_info.append({
                'path': img_path,
                'info': info,
                'date': img_date
            })
        else:
            # 即使API调用失败，也要添加到列表中
            image_info.append({
                'path': img_path,
                'info': None,
                'date': img_date
            })
    
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
            
            similarity = calculate_similarity(
                img1['info'].get('features'),
                img2['info'].get('features')
            )
            
            if similarity >= SIMILARITY_THRESHOLD:
                group.append(img2)
                processed.add(j)
        
        if len(group) > 1:
            similar_groups.append(group)
    
    # 转换结果为前端可用格式
    front_end_results = {
        'similarGroups': [],
        'allImages': []
    }
    
    # 限制相似组数量
    limited_groups = similar_groups[:30]
    for group in limited_groups:
        group_images = []
        # 限制每个组的图像数量
        limited_group_images = group[:30]
        for img in limited_group_images:
            # 读取图像并转换为base64
            with open(img['path'], 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            group_images.append({
                'name': os.path.basename(img['path']),
                'path': f"data:image/{get_image_mime_type(img['path'])};base64,{img_base64}",
                'date': img['date'].strftime('%Y-%m-%d')
            })
        
        front_end_results['similarGroups'].append({
            'images': group_images,
            'similarity': 0.85  # 模拟相似度值
        })
    
    # 限制所有图像数量
    limited_all_images = image_info[:30]
    for img in limited_all_images:
        # 读取图像并转换为base64
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
    
    # 转换结果为前端可用格式
    front_end_results = {
        'similarGroups': [],
        'allImages': []
    }
    
    # 限制相似组数量
    limited_groups = results['similar_groups'][:30]
    for group in limited_groups:
        group_images = []
        # 限制每个组的图像数量
        limited_group_images = group[:30]
        for img in limited_group_images:
            # 读取图像并转换为base64
            with open(img['path'], 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            group_images.append({
                'name': os.path.basename(img['path']),
                'path': f"data:image/{get_image_mime_type(img['path'])};base64,{img_base64}",
                'date': img['date'].strftime('%Y-%m-%d')
            })
        
        front_end_results['similarGroups'].append({
            'images': group_images,
            'similarity': 0.85  # 模拟相似度值
        })
    
    # 限制所有图像数量
    limited_all_images = results['all_images'][:30]
    for img in limited_all_images:
        # 读取图像并转换为base64
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