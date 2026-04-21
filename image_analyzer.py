import os
import requests
import json
import datetime
from PIL import Image
import numpy as np
import shutil

# 千文图像识别API配置
API_KEY = "your_api_key_here"  # 请替换为真实的API密钥
API_URL = "https://api.qianwen.com/v1/image/recognize"  # 假设的API地址

# 配置参数
SIMILARITY_THRESHOLD = 0.8  # 相似度阈值
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']

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
    # 这里使用余弦相似度，实际实现可能需要根据API返回的特征格式调整
    if not feature1 or not feature2:
        return 0.0
    # 假设feature是向量形式
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
                # 36867是拍摄日期的EXIF标签
                if 36867 in exif_data:
                    date_str = exif_data[36867]
                    return datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    # 如果没有EXIF信息，使用文件修改时间
    return datetime.datetime.fromtimestamp(os.path.getmtime(image_path))

def process_images(directory):
    """处理目录中的所有图像"""
    # 收集所有图像文件
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                image_files.append(os.path.join(root, file))
    
    print(f"找到 {len(image_files)} 个图像文件")
    
    # 识别图像并获取特征
    image_info = []
    for img_path in image_files:
        info = get_image_info(img_path)
        if info:
            image_info.append({
                'path': img_path,
                'info': info,
                'date': get_image_date(img_path)
            })
    
    # 分析相似度
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
            
            # 计算相似度
            similarity = calculate_similarity(
                img1['info'].get('features'),
                img2['info'].get('features')
            )
            
            if similarity >= SIMILARITY_THRESHOLD:
                group.append(img2)
                processed.add(j)
        
        if len(group) > 1:
            similar_groups.append(group)
    
    # 处理相似图像组
    for group in similar_groups:
        print(f"\n发现相似图像组 ({len(group)} 个图像):")
        for img in group:
            print(f"  - {os.path.basename(img['path'])}")
        
        # 手动选择是否合并
        choice = input("是否合并这些图像？(y/n): ")
        if choice.lower() == 'y':
            # 这里可以实现合并逻辑，例如保留质量最好的图像
            print("已选择合并图像")
        else:
            print("已选择不合并图像")
    
    # 按年月分类存储
    for img in image_info:
        date = img['date']
        year = str(date.year)
        month = f"{date.month:02d}"
        
        # 创建年文件夹
        year_folder = os.path.join(directory, year)
        if not os.path.exists(year_folder):
            os.makedirs(year_folder)
        
        # 创建月文件夹
        month_folder = os.path.join(year_folder, month)
        if not os.path.exists(month_folder):
            os.makedirs(month_folder)
        
        # 移动图像
        dest_path = os.path.join(month_folder, os.path.basename(img['path']))
        if not os.path.exists(dest_path):
            shutil.move(img['path'], dest_path)
            print(f"已移动 {os.path.basename(img['path'])} 到 {month_folder}")
        else:
            print(f"目标文件已存在: {dest_path}")

if __name__ == "__main__":
    # 获取当前目录
    current_dir = os.getcwd()
    print(f"开始处理目录: {current_dir}")
    process_images(current_dir)