"""
前端静态文件服务器

只提供静态文件服务，所有 API 请求转发到 Agent 应用层（app_agent.py）
"""

from flask import Flask, send_from_directory, request
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder='static')
CORS(app)

# Agent 应用层地址
AGENT_URL = "http://localhost:5001"


@app.route('/')
def index():
    """首页"""
    return send_from_directory('static', 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    """静态资源"""
    return send_from_directory('static', path)


@app.route('/digital-human-component/<path:path>')
def serve_component(path):
    """数字人组件资源"""
    return send_from_directory('digital-human-component', path)


# API 转发到 Agent 应用层
@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_api(path):
    """
    将所有 /api/* 请求转发到 Agent 应用层
    """
    url = f"{AGENT_URL}/api/{path}"

    # 转发请求
    if request.method == 'GET':
        resp = requests.get(url, params=request.args, stream=True)
    elif request.method == 'POST':
        # 处理文件上传
        files = {}
        for key in request.files:
            file = request.files[key]
            files[key] = (file.filename, file.stream, file.content_type)

        resp = requests.post(
            url,
            data=request.form,
            files=files if files else None,
            stream=True
        )
    elif request.method == 'PUT':
        resp = requests.put(url, json=request.get_json(), stream=True)
    elif request.method == 'DELETE':
        resp = requests.delete(url, params=request.args)

    # 返回响应
    from flask import Response
    return Response(
        resp.iter_content(chunk_size=8192),
        status=resp.status_code,
        headers=dict(resp.headers)
    )


if __name__ == '__main__':
    print('🚀 前端服务器启动！')
    print(f'📡 访问地址: http://localhost:5000')
    print(f'🔗 转发 API 到: {AGENT_URL}')
    print(f'💡 确保 Agent 应用层已启动: python3 app_agent.py')

    app.run(host='0.0.0.0', port=5000, debug=True)
