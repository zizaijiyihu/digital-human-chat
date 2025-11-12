#!/usr/bin/env python3
"""
测试流式 TTS 接口
"""
import requests
import sys

def test_endpoint():
    """测试新的 TTS 接口是否存在"""
    url = 'http://localhost:5001/api/video-auto-chat-with-tts'

    print(f'📡 测试接口: {url}')

    # 发送一个空请求（会失败，但能验证接口存在）
    try:
        response = requests.post(url, files={})
        print(f'✅ 接口响应: {response.status_code}')
        print(f'📝 响应内容: {response.text[:200]}')
    except Exception as e:
        print(f'❌ 错误: {e}')

if __name__ == '__main__':
    test_endpoint()
