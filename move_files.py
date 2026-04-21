import os
import shutil
from datetime import datetime
from pathlib import Path

# 定义图片和视频文件扩展名
IMAGE_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'heic',
    'raw', 'cr2', 'nef', 'orf', 'arw'
}

VIDEO_EXTENSIONS = {
    'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'm4v', 'webm', '3gp', 'mpg', 'mpeg', 'vob', 'ts'
}

def get_file_extension(filename):
    """获取文件扩展名"""
    return filename.split('.')[-1].lower() if '.' in filename else ''

def get_file_date(file_path):
    """获取文件的修改日期"""
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp)

def move_files_by_date(source_path, destination_path):
    """根据文件日期移动文件"""
    results = {
        'photos': {'moved': 0, 'failed': 0, 'files': []},
        'videos': {'moved': 0, 'failed': 0, 'files': []},
        'total_moved': 0,
        'total_failed': 0
    }
    
    source_path = Path(source_path)
    destination_path = Path(destination_path)
    
    # 检查源路径是否存在
    if not source_path.exists():
        print(f"错误：源路径不存在: {source_path}")
        return {'error': f'源路径不存在: {source_path}'}
    
    # 检查目标路径是否存在，如果不存在则创建
    if not destination_path.exists():
        print(f"目标路径不存在，正在创建...")
        destination_path.mkdir(parents=True, exist_ok=True)
    
    # 处理图片文件
    print("开始处理图片文件...")
    for file_path in source_path.rglob('*'):
        if file_path.is_file():
            ext = get_file_extension(file_path.name)
            if ext in IMAGE_EXTENSIONS:
                # 获取文件日期
                file_date = get_file_date(file_path)
                year = str(file_date.year)
                month = f"{file_date.month:02d}"
                
                # 创建年/月的文件夹结构（图片）
                date_folder = destination_path / 'photos' / year / month
                date_folder.mkdir(parents=True, exist_ok=True)
                
                # 检查目标路径中是否已存在同名文件，如果存在则添加序号
                original_filename = file_path.name
                new_filename = original_filename
                counter = 1
                while (date_folder / new_filename).exists():
                    base_name = original_filename.rsplit('.', 1)[0]
                    extension = original_filename.rsplit('.', 1)[1]
                    new_filename = f"{base_name}_{counter}.{extension}"
                    counter += 1
                
                # 移动文件到目标路径
                new_file_path = date_folder / new_filename
                try:
                    shutil.move(str(file_path), str(new_file_path))
                    results['photos']['moved'] += 1
                    results['photos']['files'].append({
                        'original': str(file_path),
                        'new': str(new_file_path),
                        'date': f"{year}/{month}"
                    })
                    results['total_moved'] += 1
                    print(f"已移动图片：{original_filename} -> photos/{year}/{month}/{new_filename}")
                except Exception as e:
                    results['photos']['failed'] += 1
                    results['total_failed'] += 1
                    print(f"移动图片失败：{original_filename} - {str(e)}")
    
    # 处理视频文件
    print("\n开始处理视频文件...")
    for file_path in source_path.rglob('*'):
        if file_path.is_file():
            ext = get_file_extension(file_path.name)
            if ext in VIDEO_EXTENSIONS:
                # 获取文件日期
                file_date = get_file_date(file_path)
                year = str(file_date.year)
                month = f"{file_date.month:02d}"
                
                # 创建年/月的文件夹结构（视频）
                date_folder = destination_path / 'videos' / year / month
                date_folder.mkdir(parents=True, exist_ok=True)
                
                # 检查目标路径中是否已存在同名文件，如果存在则添加序号
                original_filename = file_path.name
                new_filename = original_filename
                counter = 1
                while (date_folder / new_filename).exists():
                    base_name = original_filename.rsplit('.', 1)[0]
                    extension = original_filename.rsplit('.', 1)[1]
                    new_filename = f"{base_name}_{counter}.{extension}"
                    counter += 1
                
                # 移动文件到目标路径
                new_file_path = date_folder / new_filename
                try:
                    shutil.move(str(file_path), str(new_file_path))
                    results['videos']['moved'] += 1
                    results['videos']['files'].append({
                        'original': str(file_path),
                        'new': str(new_file_path),
                        'date': f"{year}/{month}"
                    })
                    results['total_moved'] += 1
                    print(f"已移动视频：{original_filename} -> videos/{year}/{month}/{new_filename}")
                except Exception as e:
                    results['videos']['failed'] += 1
                    results['total_failed'] += 1
                    print(f"移动视频失败：{original_filename} - {str(e)}")
    
    print("\n文件移动完成！")
    return results

def main():
    """主函数"""
    # 提示用户输入源路径
    source_path = input("请输入源路径（例如：D:/path/to/source）：")
    
    # 提示用户输入目标路径
    destination_path = input("请输入目标路径（例如：D:/path/to/destination）：")
    
    # 调用移动文件函数
    move_files_by_date(source_path, destination_path)

if __name__ == "__main__":
    main()
