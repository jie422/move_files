#!/bin/bash

# 定义图片和视频文件扩展名
image_extensions=(
    "jpg" "jpeg" "png" "gif" "bmp" "webp" "tiff" "heic" 
    "raw" "cr2" "nef" "orf" "arw"
)

video_extensions=(
    "mp4" "avi" "mov" "mkv" "wmv" "flv" "m4v" "webm" "3gp" "mpg" "mpeg" "vob" "ts"
)

# 提示用户输入源路径
echo "请输入源路径（例如：/path/to/source）："
read source_path

# 提示用户输入目标路径
echo "请输入目标路径（例如：/path/to/destination）："
read destination_path

# 检查目标路径是否存在，如果不存在则创建
if [ ! -d "$destination_path" ]; then
    echo "目标路径不存在，正在创建..."
    mkdir -p "$destination_path"
fi

# 处理图片文件
echo "开始处理图片文件..."
find "$source_path" -type f \( \
    -iname "*.jpg" -o \
    -iname "*.jpeg" -o \
    -iname "*.png" -o \
    -iname "*.gif" -o \
    -iname "*.bmp" -o \
    -iname "*.webp" -o \
    -iname "*.tiff" -o \
    -iname "*.heic" -o \
    -iname "*.raw" -o \
    -iname "*.cr2" -o \
    -iname "*.nef" -o \
    -iname "*.orf" -o \
    -iname "*.arw" \
\) | while read file; do
    # 获取文件的修改日期（年-月-日）
    file_date=$(stat -c %y "$file" | cut -d' ' -f1)
    year=$(echo $file_date | cut -d'-' -f1)
    month=$(echo $file_date | cut -d'-' -f2)
    
    # 创建年/月的文件夹结构（图片）
    date_folder="$destination_path/photos/$year/$month"
    mkdir -p "$date_folder"

    # 检查目标路径中是否已存在同名文件，如果存在则添加序号
    original_filename=$(basename "$file")
    new_filename="$original_filename"
    counter=1
    while [ -f "$date_folder/$new_filename" ]; do
        base_name="${original_filename%.*}"
        extension="${original_filename##*.}"
        new_filename="${base_name}_${counter}.${extension}"
        counter=$((counter + 1))
    done

    # 移动文件到目标路径（保持原文件名）
    mv "$file" "$date_folder/$new_filename"
    echo "已移动图片：$(basename "$file") -> photos/$year/$month/$new_filename"
done

# 处理视频文件
echo "\n开始处理视频文件..."
find "$source_path" -type f \( \
    -iname "*.mp4" -o \
    -iname "*.avi" -o \
    -iname "*.mov" -o \
    -iname "*.mkv" -o \
    -iname "*.wmv" -o \
    -iname "*.flv" -o \
    -iname "*.m4v" -o \
    -iname "*.webm" -o \
    -iname "*.3gp" -o \
    -iname "*.mpg" -o \
    -iname "*.mpeg" -o \
    -iname "*.vob" -o \
    -iname "*.ts" \
\) | while read file; do
    # 获取文件的修改日期（年-月-日）
    file_date=$(stat -c %y "$file" | cut -d' ' -f1)
    year=$(echo $file_date | cut -d'-' -f1)
    month=$(echo $file_date | cut -d'-' -f2)
    
    # 创建年/月的文件夹结构（视频）
    date_folder="$destination_path/videos/$year/$month"
    mkdir -p "$date_folder"

    # 检查目标路径中是否已存在同名文件，如果存在则添加序号
    original_filename=$(basename "$file")
    new_filename="$original_filename"
    counter=1
    while [ -f "$date_folder/$new_filename" ]; do
        base_name="${original_filename%.*}"
        extension="${original_filename##*.}"
        new_filename="${base_name}_${counter}.${extension}"
        counter=$((counter + 1))
    done

    # 移动文件到目标路径（保持原文件名）
    mv "$file" "$date_folder/$new_filename"
    echo "已移动视频：$(basename "$file") -> videos/$year/$month/$new_filename"
done

echo "\n文件移动完成！"
