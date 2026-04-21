import os
import webbrowser
from flask import Flask, request, jsonify
from move_files import move_files_by_date

app = Flask(__name__)

@app.route('/api/organize', methods=['GET'])
def api_organize():
    """处理文件移动请求"""
    source_path = request.args.get('source_path')
    destination_path = request.args.get('destination_path')
    
    if not source_path or not destination_path:
        return jsonify({'error': '缺少源路径或目标路径'})
    
    try:
        # 调用move_files_by_date函数
        results = move_files_by_date(source_path, destination_path)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/')
def index():
    """返回前端页面"""
    return open('move_files.html', encoding='utf-8').read()

def main():
    """主函数"""
    # 自动打开HTML页面
    webbrowser.open('http://127.0.0.1:5000')
    # 启动Flask应用
    app.run(debug=True, port=5000)

if __name__ == "__main__":
    main()
