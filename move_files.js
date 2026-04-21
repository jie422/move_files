const fs = require('fs');
const path = require('path');

// 定义图片和视频文件扩展名
const IMAGE_EXTENSIONS = new Set([
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'heic',
    'raw', 'cr2', 'nef', 'orf', 'arw'
]);

const VIDEO_EXTENSIONS = new Set([
    'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'm4v', 'webm', '3gp', 'mpg', 'mpeg', 'vob', 'ts'
]);

/**
 * 获取文件扩展名
 * @param {string} filename 文件名
 * @returns {string} 文件扩展名
 */
function getFileExtension(filename) {
    return filename.includes('.') ? filename.split('.').pop().toLowerCase() : '';
}

/**
 * 获取文件的修改日期
 * @param {string} filePath 文件路径
 * @returns {Date} 文件修改日期
 */
function getFileDate(filePath) {
    const stats = fs.statSync(filePath);
    return new Date(stats.mtime);
}

/**
 * 递归遍历目录
 * @param {string} dir 目录路径
 * @returns {Array} 文件路径列表
 */
function walk(dir) {
    let files = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            files = files.concat(walk(fullPath));
        } else {
            files.push(fullPath);
        }
    }
    
    return files;
}

/**
 * 确保目录存在
 * @param {string} dir 目录路径
 */
function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

/**
 * 根据文件日期移动文件
 * @param {string} sourcePath 源路径
 * @param {string} destinationPath 目标路径
 * @returns {Object} 移动结果
 */
function moveFilesByDate(sourcePath, destinationPath) {
    const results = {
        photos: { moved: 0, failed: 0, files: [] },
        videos: { moved: 0, failed: 0, files: [] },
        total_moved: 0,
        total_failed: 0
    };
    
    // 检查源路径是否存在
    if (!fs.existsSync(sourcePath)) {
        console.log(`错误：源路径不存在: ${sourcePath}`);
        return { error: `源路径不存在: ${sourcePath}` };
    }
    
    // 检查目标路径是否存在，如果不存在则创建
    if (!fs.existsSync(destinationPath)) {
        console.log(`目标路径不存在，正在创建...`);
        ensureDir(destinationPath);
    }
    
    // 处理图片文件
    console.log("开始处理图片文件...");
    const allFiles = walk(sourcePath);
    
    for (const filePath of allFiles) {
        const ext = getFileExtension(filePath);
        if (IMAGE_EXTENSIONS.has(ext)) {
            // 获取文件日期
            const fileDate = getFileDate(filePath);
            const year = fileDate.getFullYear().toString();
            const month = String(fileDate.getMonth() + 1).padStart(2, '0');
            
            // 创建年/月的文件夹结构（图片）
            const dateFolder = path.join(destinationPath, 'photos', year, month);
            ensureDir(dateFolder);
            
            // 检查目标路径中是否已存在同名文件，如果存在则添加序号
            const originalFilename = path.basename(filePath);
            let newFilename = originalFilename;
            let counter = 1;
            
            while (fs.existsSync(path.join(dateFolder, newFilename))) {
                const baseName = originalFilename.split('.').slice(0, -1).join('.');
                const extension = originalFilename.split('.').pop();
                newFilename = `${baseName}_${counter}.${extension}`;
                counter++;
            }
            
            // 移动文件到目标路径
            const newFilePath = path.join(dateFolder, newFilename);
            try {
                fs.renameSync(filePath, newFilePath);
                results.photos.moved++;
                results.photos.files.push({
                    original: filePath,
                    new: newFilePath,
                    date: `${year}/${month}`
                });
                results.total_moved++;
                console.log(`已移动图片：${originalFilename} -> photos/${year}/${month}/${newFilename}`);
            } catch (e) {
                results.photos.failed++;
                results.total_failed++;
                console.log(`移动图片失败：${originalFilename} - ${e.message}`);
            }
        }
    }
    
    // 处理视频文件
    console.log("\n开始处理视频文件...");
    for (const filePath of allFiles) {
        const ext = getFileExtension(filePath);
        if (VIDEO_EXTENSIONS.has(ext)) {
            // 获取文件日期
            const fileDate = getFileDate(filePath);
            const year = fileDate.getFullYear().toString();
            const month = String(fileDate.getMonth() + 1).padStart(2, '0');
            
            // 创建年/月的文件夹结构（视频）
            const dateFolder = path.join(destinationPath, 'videos', year, month);
            ensureDir(dateFolder);
            
            // 检查目标路径中是否已存在同名文件，如果存在则添加序号
            const originalFilename = path.basename(filePath);
            let newFilename = originalFilename;
            let counter = 1;
            
            while (fs.existsSync(path.join(dateFolder, newFilename))) {
                const baseName = originalFilename.split('.').slice(0, -1).join('.');
                const extension = originalFilename.split('.').pop();
                newFilename = `${baseName}_${counter}.${extension}`;
                counter++;
            }
            
            // 移动文件到目标路径
            const newFilePath = path.join(dateFolder, newFilename);
            try {
                fs.renameSync(filePath, newFilePath);
                results.videos.moved++;
                results.videos.files.push({
                    original: filePath,
                    new: newFilePath,
                    date: `${year}/${month}`
                });
                results.total_moved++;
                console.log(`已移动视频：${originalFilename} -> videos/${year}/${month}/${newFilename}`);
            } catch (e) {
                results.videos.failed++;
                results.total_failed++;
                console.log(`移动视频失败：${originalFilename} - ${e.message}`);
            }
        }
    }
    
    console.log("\n文件移动完成！");
    return results;
}

/**
 * 主函数
 */
function main() {
    // 提示用户输入源路径
    const readline = require('readline').createInterface({
        input: process.stdin,
        output: process.stdout
    });
    
    readline.question('请输入源路径（例如：D:/path/to/source）：', (sourcePath) => {
        readline.question('请输入目标路径（例如：D:/path/to/destination）：', (destinationPath) => {
            // 调用移动文件函数
            moveFilesByDate(sourcePath, destinationPath);
            readline.close();
        });
    });
}

// 如果直接运行此文件，则执行主函数
if (require.main === module) {
    main();
}

// 导出函数
module.exports = { moveFilesByDate };
