const express = require('express');
const path = require('path');
const { moveFilesByDate } = require('./move_files.js');

const app = express();
const port = 3000;

// 静态文件服务
app.use(express.static(__dirname));

// API路由
app.get('/api/organize', (req, res) => {
    const sourcePath = req.query.source_path;
    const destinationPath = req.query.destination_path;
    
    if (!sourcePath || !destinationPath) {
        res.json({ error: '缺少源路径或目标路径' });
        return;
    }
    
    try {
        const results = moveFilesByDate(sourcePath, destinationPath);
        res.json(results);
    } catch (error) {
        res.json({ error: error.message });
    }
});

// 首页路由
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'move_files_js.html'));
});

// 启动服务器
app.listen(port, () => {
    console.log(`服务器运行在 http://localhost:${port}`);
    console.log('前端页面：http://localhost:3000');
});
