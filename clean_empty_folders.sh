#!/bin/bash

# 提示用户输入要清理的路径
echo "请输入要清理空文件夹的路径（例如：/path/to/folder）："
read target_path

# 检查路径是否存在
if [ ! -d "$target_path" ]; then
    echo "错误：指定的路径不存在或不是一个文件夹！"
    exit 1
fi

echo "开始清理空文件夹..."

# 递归删除空文件夹（从最深层开始）
find "$target_path" -type d -empty | sort -r | while read folder; do
    echo "删除空文件夹：$folder"
    rmdir "$folder"
done

echo "空文件夹清理完成！"
