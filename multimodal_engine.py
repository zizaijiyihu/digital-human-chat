"""
多模态引擎 - 内部工具模块

提供基础的多模态 AI 能力，不对外暴露接口
"""

import dashscope
from openai import OpenAI
import os

# 从环境变量读取配置
API_KEY = os.getenv('API_KEY')  # 使用统一的 API_KEY 环境变量
if not API_KEY:
    raise ValueError('请设置环境变量 API_KEY')

API_BASE = os.getenv('API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
MODEL = os.getenv('MODEL', 'qwen3-omni-flash')

# 初始化 OpenAI 客户端（兼容模式）
client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE
)

# 配置 DashScope SDK
dashscope.api_key = API_KEY
dashscope.base_http_api_url = API_BASE.replace('/compatible-mode/v1', '/api/v1')


def multimodal_chat(messages, modalities=['text'], stream=False):
    """
    多模态对话

    参数:
        messages: 消息列表，支持 text/video_url/audio_url/image_url
        modalities: 输出模态 ['text'] 或 ['text', 'audio']
        stream: 是否流式返回

    返回:
        response: AI 响应对象

    示例:
        response = multimodal_chat(
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant'},
                {
                    'role': 'user',
                    'content': [
                        {'type': 'video_url', 'video_url': {'url': 'data:video/webm;base64,...'}}
                    ]
                }
            ],
            modalities=['text'],
            stream=False
        )
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            modalities=modalities,
            stream=stream
        )
        return response
    except Exception as e:
        print(f'❌ 多模态对话失败: {e}')
        raise


def stream_tts(text, voice='Cherry', language='Chinese'):
    """
    流式 TTS 合成

    参数:
        text: 要合成的文本
        voice: 声音类型（Cherry/Bella/Rocky/...）
        language: 语言（Chinese/English）

    返回:
        generator: 音频流生成器，产出 PCM 格式音频数据

    示例:
        audio_stream = stream_tts("你好，我是数字人")
        for chunk in audio_stream:
            yield chunk
    """
    try:
        responses = dashscope.MultiModalConversation.call(
            model="qwen3-tts-flash",
            text=text,
            voice=voice,
            language_type=language,
            stream=True
        )

        for response in responses:
            if response.status_code == 200:
                # 返回音频数据
                if hasattr(response, 'output') and 'audio' in response.output:
                    for audio_chunk in response.output['audio']:
                        yield audio_chunk
            else:
                print(f'❌ TTS 合成失败: {response.code} - {response.message}')
                raise Exception(f'TTS 合成失败: {response.code} - {response.message}')

    except Exception as e:
        print(f'❌ TTS 合成异常: {e}')
        raise


def text_chat(messages, stream=False):
    """
    纯文本对话（更快，不支持多模态输入）

    参数:
        messages: 消息列表（只支持文本）
        stream: 是否流式返回

    返回:
        response: AI 响应对象

    示例:
        response = text_chat(
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant'},
                {'role': 'user', 'content': '你好'}
            ]
        )
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=stream
        )
        return response
    except Exception as e:
        print(f'❌ 文本对话失败: {e}')
        raise


# 工具函数：将文件转为 base64
def file_to_base64(file_path):
    """将文件转换为 base64 编码"""
    import base64
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


# 工具函数：检测 MIME 类型
def detect_mime_type(filename):
    """根据文件扩展名检测 MIME 类型"""
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'
