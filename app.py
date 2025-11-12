"""
数字人对话系统
支持视频输入，返回音频输出驱动数字人
"""

import os
import base64
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from openai import OpenAI
import dashscope
import tempfile
import subprocess
import traceback

app = Flask(__name__, static_folder='static')

# 配置（从环境变量读取）
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError('请设置环境变量 API_KEY')

API_BASE = os.getenv('API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
MODEL = os.getenv('MODEL', 'qwen3-omni-flash')  # 支持音频输出的模型

# 音频转换方式配置
# 'wav' - 添加 WAV 文件头（推荐，延迟最低）
# 'mp3' - 使用 FFmpeg 转换为 MP3（延迟较高，兼容性好）
AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'wav')

# OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=API_BASE)

# 配置 DashScope SDK
dashscope.api_key = API_KEY
dashscope.base_http_api_url = API_BASE.replace('/compatible-mode/v1', '/api/v1')

# 确保目录存在
Path('test/videos').mkdir(parents=True, exist_ok=True)
Path('test/audios').mkdir(parents=True, exist_ok=True)
Path('static/videos').mkdir(parents=True, exist_ok=True)


# 全局变量：系统提示词（从文件加载）
def load_system_prompt():
    """从 system_prompt.md 文件加载系统提示词"""
    prompt_file = Path('system_prompt.md')
    if prompt_file.exists():
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f'✅ 已加载系统提示词文件: {prompt_file} ({len(content)} 字符)')
            return content
    else:
        default_prompt = "你是一个友好、专业的AI助手。请仔细观看用户的视频，理解其中的内容和问题，用清晰、自然的语气回复。"
        print(f'⚠️ 未找到 system_prompt.md，使用默认提示词')
        return default_prompt

system_prompt = load_system_prompt()

# 视频保存记录
latest_videos = {
    'segments': [],
    'merged': None,
    'timestamp': None
}


def convert_webm_to_mp4(webm_data):
    """将 WebM 视频转换为 MP4 格式"""
    print(f'🔄 开始转换视频，输入大小: {len(webm_data)} bytes')

    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as input_file:
        input_file.write(webm_data)
        input_path = input_file.name

    print(f'📁 临时输入文件: {input_path}')

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
        output_path = output_file.name

    print(f'📁 临时输出文件: {output_path}')

    try:
        result = subprocess.run([
            'ffmpeg', '-y', '-i', input_path,
            '-vcodec', 'libx264', '-acodec', 'aac',
            '-preset', 'ultrafast', '-crf', '28',
            output_path
        ], check=True, capture_output=True, text=True)

        print(f'✅ FFmpeg 转换成功')

        with open(output_path, 'rb') as f:
            mp4_data = f.read()

        print(f'📦 转换后 MP4 大小: {len(mp4_data)} bytes')

        return mp4_data
    except subprocess.CalledProcessError as e:
        print(f'❌ FFmpeg 转换失败 (退出码 {e.returncode}):')
        print(f'=== FFmpeg stdout ===')
        print(e.stdout)
        print(f'=== FFmpeg stderr ===')
        print(e.stderr)
        print(f'=====================')
        raise Exception(f'FFmpeg conversion failed (exit code {e.returncode}): {e.stderr[:200]}')
    finally:
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def add_wav_header(pcm_data, sample_rate=24000, bits_per_sample=16, channels=1):
    """
    给 PCM 数据添加 WAV 文件头

    参数:
        pcm_data: 原始 PCM 数据 (bytes)
        sample_rate: 采样率 (默认 24000 Hz，阿里云默认)
        bits_per_sample: 位深度 (默认 16-bit)
        channels: 声道数 (默认 1 单声道)

    返回:
        带 WAV 文件头的完整音频数据
    """
    import struct

    print(f'🔄 添加 WAV 文件头，PCM 大小: {len(pcm_data)} bytes')

    # 计算各种参数
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm_data)
    file_size = data_size + 36  # 44 bytes header - 8 bytes

    # 构建 WAV 文件头 (44 bytes)
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',           # ChunkID
        file_size,         # ChunkSize
        b'WAVE',           # Format
        b'fmt ',           # Subchunk1ID
        16,                # Subchunk1Size (16 for PCM)
        1,                 # AudioFormat (1 for PCM)
        channels,          # NumChannels
        sample_rate,       # SampleRate
        byte_rate,         # ByteRate
        block_align,       # BlockAlign
        bits_per_sample,   # BitsPerSample
        b'data',           # Subchunk2ID
        data_size          # Subchunk2Size
    )

    wav_data = header + pcm_data
    print(f'✅ WAV 文件头添加完成，总大小: {len(wav_data)} bytes')

    return wav_data


def convert_pcm_to_mp3(pcm_data):
    """将 PCM 音频数据转换为 MP3 格式 (使用 FFmpeg)"""
    print(f'🔄 开始转换音频 PCM -> MP3，输入大小: {len(pcm_data)} bytes')

    # 保存 PCM 数据到临时文件
    with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as input_file:
        input_file.write(pcm_data)
        input_path = input_file.name

    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as output_file:
        output_path = output_file.name

    try:
        # 使用 ffmpeg 将 PCM 转换为 MP3
        # 阿里云返回的应该是 16-bit, 24kHz, mono PCM
        result = subprocess.run([
            'ffmpeg', '-y',
            '-f', 's16le',  # 16-bit signed little-endian
            '-ar', '24000',  # 24kHz sample rate
            '-ac', '1',  # mono
            '-i', input_path,
            '-codec:a', 'libmp3lame',
            '-b:a', '128k',
            output_path
        ], check=True, capture_output=True, text=True)

        print(f'✅ 音频转换成功')

        with open(output_path, 'rb') as f:
            mp3_data = f.read()

        print(f'📦 转换后 MP3 大小: {len(mp3_data)} bytes')

        return mp3_data
    except subprocess.CalledProcessError as e:
        print(f'❌ 音频转换失败:')
        print(f'stdout: {e.stdout}')
        print(f'stderr: {e.stderr}')
        raise
    finally:
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


@app.route('/')
def index():
    """主页"""
    return send_from_directory('static', 'index.html')


@app.route('/digital-human-component/<path:filename>')
def serve_digital_human(filename):
    """提供 digital-human-component 静态文件"""
    return send_from_directory('digital-human-component', filename)


@app.route('/test/audios/<filename>')
def serve_test_audio(filename):
    """提供测试音频文件的 HTTP 访问"""
    return send_from_directory('test/audios', filename)


@app.route('/api/image-commentary-streaming', methods=['POST'])
def image_commentary_streaming():
    """
    处理图片点评（流式返回）
    接收图片，实时流式返回音频点评
    """
    try:
        print('\n' + '='*80)
        print('🎯 收到流式图片点评请求')
        print('='*80)

        # 获取图片
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({'error': '缺少图片文件'}), 400

        # 读取图片数据
        image_data = image_file.read()
        print(f'📦 图片大小: {len(image_data)} bytes')

        # Base64 编码图片
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # 获取图片格式（从文件名）
        filename = image_file.filename.lower()
        if filename.endswith('.jpg') or filename.endswith('.jpeg'):
            image_format = 'jpeg'
        elif filename.endswith('.png'):
            image_format = 'png'
        elif filename.endswith('.gif'):
            image_format = 'gif'
        elif filename.endswith('.webp'):
            image_format = 'webp'
        else:
            # 默认 jpeg
            image_format = 'jpeg'

        print(f'🖼️ 图片格式: {image_format}')
        print(f'🔐 Base64 编码长度: {len(image_base64)} 字符')

        # 调用大模型（qwen3-omni-flash 支持图片输入和音频输出）
        print(f'⏳ 调用大模型 {MODEL}...')

        # 使用 data URI 格式（与官方示例类似）
        image_data_uri = f'data:image/{image_format};base64,{image_base64}'

        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': image_data_uri
                            }
                        },
                        {
                            'type': 'text',
                            'text': '请详细点评这张图片，描述图片的内容、构图、色彩、意境等方面。'
                        }
                    ]
                }
            ],
            modalities=['text', 'audio'],  # 请求音频输出
            audio={'voice': 'Cherry', 'format': 'wav'},
            stream=True,
            stream_options={'include_usage': True}
        )

        print('✅ 开始流式返回音频片段')

        def generate():
            """生成器函数，累积音频后返回较大的片段"""
            text_content = ''
            audio_chunk_count = 0
            pcm_buffer = b''  # PCM 缓冲区
            MIN_CHUNK_SIZE = 24000  # 最小块大小：24KB (约 0.5 秒音频 @ 24kHz 16-bit mono)
            # 更小的块可以减少队列积压，避免 "Queue is full" 警告

            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta

                    # 收集文本（用于日志）
                    if hasattr(delta, 'content') and delta.content:
                        text_content += delta.content
                        print(f'📝 文本片段: {delta.content}')

                    # 累积音频片段
                    if hasattr(delta, 'audio') and delta.audio:
                        if isinstance(delta.audio, dict) and 'data' in delta.audio:
                            audio_data_chunk = delta.audio['data']

                            # 解码 base64 音频数据并累积到缓冲区
                            pcm_chunk = base64.b64decode(audio_data_chunk)
                            pcm_buffer += pcm_chunk
                            print(f'🔊 累积音频数据: +{len(pcm_chunk)} bytes, 总计: {len(pcm_buffer)} bytes')

                            # 当缓冲区达到最小大小时，返回一个完整的 WAV 块
                            if len(pcm_buffer) >= MIN_CHUNK_SIZE:
                                audio_chunk_count += 1
                                wav_chunk = add_wav_header(pcm_buffer)
                                print(f'✅ 返回音频块 #{audio_chunk_count}: {len(wav_chunk)} bytes')
                                yield wav_chunk
                                pcm_buffer = b''  # 清空缓冲区
                else:
                    # 打印使用统计
                    if hasattr(chunk, 'usage') and chunk.usage:
                        print(f'📊 Token 使用: {chunk.usage}')

            # 返回剩余的音频数据（如果有）
            if pcm_buffer:
                audio_chunk_count += 1
                wav_chunk = add_wav_header(pcm_buffer)
                print(f'✅ 返回最后的音频块 #{audio_chunk_count}: {len(wav_chunk)} bytes')
                yield wav_chunk

            print(f'✅ 流式返回完成')
            print(f'📝 完整文本: {text_content}')
            print(f'🔊 总共返回 {audio_chunk_count} 个音频块')

        # 返回流式响应
        return Response(generate(), mimetype='application/octet-stream')

    except Exception as e:
        print(f'❌ 错误: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/audio-chat-streaming', methods=['POST'])
def audio_chat_streaming():
    """
    处理音频对话（流式返回）
    接收音频，实时流式返回音频片段
    """
    try:
        print('\n' + '='*80)
        print('🎯 收到流式音频对话请求')
        print('='*80)

        # 获取音频
        audio_file = request.files.get('audio')
        if not audio_file:
            return jsonify({'error': '缺少音频文件'}), 400

        # 读取音频数据（WebM 格式）
        webm_data = audio_file.read()
        print(f'📦 WebM 音频大小: {len(webm_data)} bytes')

        # 转换 WebM 音频为 WAV 格式（阿里云 API 支持 WAV 格式）
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as input_file:
            input_file.write(webm_data)
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
            output_path = output_file.name

        try:
            print('🔄 正在将 WebM 转换为 WAV 格式...')
            # 转换为 WAV 格式
            subprocess.run([
                'ffmpeg', '-y', '-i', input_path,
                '-ar', '24000',  # 采样率 24kHz (阿里云推荐)
                '-ac', '1',  # 单声道
                '-sample_fmt', 's16',  # 16位采样
                output_path
            ], check=True, capture_output=True, text=True)

            with open(output_path, 'rb') as f:
                wav_data = f.read()

            print(f'📦 转换后 WAV 大小: {len(wav_data)} bytes')

            # Base64 编码
            audio_base64 = base64.b64encode(wav_data).decode('utf-8')
            print(f'🔐 Base64 编码长度: {len(audio_base64)} 字符')

        finally:
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

        # 调用大模型（qwen3-omni-flash 支持音频输入和输出）
        print(f'⏳ 调用大模型 {MODEL}...')

        # 使用 data URI 格式（与视频输入相同的方式）
        audio_data_uri = f'data:audio/wav;base64,{audio_base64}'
        print(f'🔗 音频 Data URI 长度: {len(audio_data_uri)} 字符')

        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_audio',
                            'input_audio': {
                                'data': audio_data_uri,  # 使用 data URI（与视频相同）
                                'format': 'wav'
                            }
                        },
                        {
                            'type': 'text',
                            'text': '请理解这段音频中的内容和问题，并用语音回复我'
                        }
                    ]
                }
            ],
            modalities=['text', 'audio'],  # 请求音频输出
            audio={'voice': 'Cherry', 'format': 'wav'},
            stream=True,
            stream_options={'include_usage': True}
        )

        print('✅ 开始流式返回音频片段')

        def generate():
            """生成器函数，累积音频后返回较大的片段"""
            text_content = ''
            audio_chunk_count = 0
            pcm_buffer = b''  # PCM 缓冲区
            MIN_CHUNK_SIZE = 24000  # 最小块大小：24KB (约 0.5 秒音频 @ 24kHz 16-bit mono)
            # 更小的块可以减少队列积压，避免 "Queue is full" 警告

            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta

                    # 收集文本（用于日志）
                    if hasattr(delta, 'content') and delta.content:
                        text_content += delta.content
                        print(f'📝 文本片段: {delta.content}')

                    # 累积音频片段
                    if hasattr(delta, 'audio') and delta.audio:
                        if isinstance(delta.audio, dict) and 'data' in delta.audio:
                            audio_data_chunk = delta.audio['data']

                            # 解码 base64 音频数据并累积到缓冲区
                            pcm_chunk = base64.b64decode(audio_data_chunk)
                            pcm_buffer += pcm_chunk
                            print(f'🔊 累积音频数据: +{len(pcm_chunk)} bytes, 总计: {len(pcm_buffer)} bytes')

                            # 当缓冲区达到最小大小时，返回一个完整的 WAV 块
                            if len(pcm_buffer) >= MIN_CHUNK_SIZE:
                                audio_chunk_count += 1
                                wav_chunk = add_wav_header(pcm_buffer)
                                print(f'✅ 返回音频块 #{audio_chunk_count}: {len(wav_chunk)} bytes')
                                yield wav_chunk
                                pcm_buffer = b''  # 清空缓冲区
                else:
                    # 打印使用统计
                    if hasattr(chunk, 'usage') and chunk.usage:
                        print(f'📊 Token 使用: {chunk.usage}')

            # 返回剩余的音频数据（如果有）
            if pcm_buffer:
                audio_chunk_count += 1
                wav_chunk = add_wav_header(pcm_buffer)
                print(f'✅ 返回最后的音频块 #{audio_chunk_count}: {len(wav_chunk)} bytes')
                yield wav_chunk

            print(f'✅ 流式返回完成')
            print(f'📝 完整文本: {text_content}')
            print(f'🔊 总共返回 {audio_chunk_count} 个音频块')

        # 返回流式响应
        return Response(generate(), mimetype='application/octet-stream')

    except Exception as e:
        print(f'❌ 错误: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/audio-chat', methods=['POST'])
def audio_chat():
    """
    处理音频对话（非流式，保留用于兼容）
    接收音频，返回音频
    """
    try:
        print('\n' + '='*80)
        print('🎯 收到音频对话请求')
        print('='*80)

        # 获取音频
        audio_file = request.files.get('audio')
        if not audio_file:
            return jsonify({'error': '缺少音频文件'}), 400

        # 读取音频数据（WebM 格式）
        webm_data = audio_file.read()
        print(f'📦 WebM 音频大小: {len(webm_data)} bytes')

        # 转换 WebM 音频为 WAV 格式（阿里云 API 支持 WAV 格式）
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as input_file:
            input_file.write(webm_data)
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
            output_path = output_file.name

        try:
            print('🔄 正在将 WebM 转换为 WAV 格式...')
            # 转换为 WAV 格式
            subprocess.run([
                'ffmpeg', '-y', '-i', input_path,
                '-ar', '24000',  # 采样率 24kHz (阿里云推荐)
                '-ac', '1',  # 单声道
                '-sample_fmt', 's16',  # 16位采样
                output_path
            ], check=True, capture_output=True, text=True)

            with open(output_path, 'rb') as f:
                wav_data = f.read()

            print(f'📦 转换后 WAV 大小: {len(wav_data)} bytes')

            # Base64 编码
            audio_base64 = base64.b64encode(wav_data).decode('utf-8')
            print(f'🔐 Base64 编码长度: {len(audio_base64)} 字符')

        finally:
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

        # 调用大模型（qwen3-omni-flash 支持音频输入和输出）
        print(f'⏳ 调用大模型 {MODEL}...')

        # 使用官方文档中的 input_audio 类型
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_audio',
                            'input_audio': {
                                'data': audio_base64,  # 直接传 base64 字符串
                                'format': 'wav'
                            }
                        },
                        {
                            'type': 'text',
                            'text': '请理解这段音频中的内容和问题，并用语音回复我'
                        }
                    ]
                }
            ],
            modalities=['text', 'audio'],  # 请求音频输出
            audio={'voice': 'Cherry', 'format': 'wav'},
            stream=True,
            stream_options={'include_usage': True}
        )

        print('✅ 开始接收流式响应')

        # 收集文本和音频
        text_content = ''
        audio_chunks = []

        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta

                # 收集文本
                if hasattr(delta, 'content') and delta.content:
                    text_content += delta.content
                    print(f'📝 文本片段: {delta.content}')

                # 收集音频
                if hasattr(delta, 'audio') and delta.audio:
                    if isinstance(delta.audio, dict) and 'data' in delta.audio:
                        audio_data_chunk = delta.audio['data']
                        audio_chunks.append(audio_data_chunk)
                        print(f'🔊 收到音频片段: {len(audio_data_chunk)} 字符')
            else:
                # 打印使用统计
                if hasattr(chunk, 'usage') and chunk.usage:
                    print(f'📊 Token 使用: {chunk.usage}')

        print(f'✅ 流式响应接收完成')
        print(f'📝 完整文本: {text_content}')
        print(f'🔊 音频片段数: {len(audio_chunks)}')

        # 合并音频
        audio_data = None
        audio_format = AUDIO_FORMAT
        if audio_chunks:
            pcm_data = b''.join([base64.b64decode(chunk) for chunk in audio_chunks])
            print(f'🔊 合并后 PCM 音频大小: {len(pcm_data)} bytes')

            # 根据配置选择转换方式
            try:
                if AUDIO_FORMAT == 'mp3':
                    print('📝 使用 MP3 转换方式')
                    audio_data = convert_pcm_to_mp3(pcm_data)
                    file_ext = 'mp3'
                else:
                    print('📝 使用 WAV 文件头方式')
                    audio_data = add_wav_header(pcm_data)
                    audio_format = 'wav'
                    file_ext = 'wav'

                # 保存音频到测试目录
                import time
                audio_path = f'test/audios/audio_response_{int(time.time())}.{file_ext}'
                with open(audio_path, 'wb') as f:
                    f.write(audio_data)
                print(f'💾 音频已保存: {audio_path}')
            except Exception as e:
                print(f'⚠️  音频转换失败: {e}')
                import traceback
                traceback.print_exc()
                audio_data = None

        # 如果没有音频，只返回文本
        if not audio_data:
            print('⚠️  未收到音频，只返回文本')
            return jsonify({
                'success': True,
                'text': text_content,
                'hasAudio': False
            })

        # 返回音频（base64）
        return jsonify({
            'success': True,
            'text': text_content,
            'hasAudio': True,
            'audio': base64.b64encode(audio_data).decode('utf-8'),
            'audioFormat': audio_format
        })

    except Exception as e:
        print(f'❌ 错误: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/video-auto-chat', methods=['POST'])
def video_auto_chat():
    """
    处理视频自动采集对话（流式返回）
    接收单个或多个视频片段，自动合并后发送给 AI，实时流式返回音频片段
    """
    try:
        print('\n' + '='*80)
        print('🎯 收到视频自动采集对话请求')
        print('='*80)

        # 获取视频文件列表
        video_files = request.files.getlist('videos')
        if not video_files:
            return jsonify({'error': '缺少视频文件'}), 400

        print(f'📦 收到 {len(video_files)} 个视频片段')

        # 如果只有一个视频，转换为 MP4（Qwen API 不支持 WebM）
        if len(video_files) == 1:
            print('📹 单个视频片段，转换为 MP4（Qwen API 要求）')
            webm_data = video_files[0].read()
            print(f'📦 WebM 大小: {len(webm_data)} bytes')

            # 转换为 MP4
            video_data = convert_webm_to_mp4(webm_data)
            video_mime = 'video/mp4'
            print(f'✅ MP4 转换成功，大小: {len(video_data)} bytes')
        else:
            # 多个视频，使用 ffmpeg 合并为 MP4
            print(f'🔀 多个视频片段，开始合并 {len(video_files)} 个片段')

            # 保存所有 WebM 文件到临时文件
            temp_webm_files = []
            temp_mp4_files = []

            for i, video_file in enumerate(video_files):
                webm_data = video_file.read()
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                    f.write(webm_data)
                    temp_webm_files.append(f.name)
                    print(f'  📁 片段 {i+1}: {f.name} ({len(webm_data)} bytes)')

            # 将所有 WebM 转换为 MP4（ffmpeg 合并 MP4 更可靠）
            print('🔄 第一步：将所有 WebM 转换为 MP4...')
            for i, webm_path in enumerate(temp_webm_files):
                mp4_path = webm_path.replace('.webm', '.mp4')
                try:
                    print(f'  🔄 正在转换片段 {i+1}...')
                    result = subprocess.run([
                        'ffmpeg', '-y', '-i', webm_path,
                        '-vcodec', 'libx264', '-acodec', 'aac',
                        '-preset', 'ultrafast', '-crf', '28',
                        mp4_path
                    ], check=True, capture_output=True, text=True)
                    temp_mp4_files.append(mp4_path)
                    print(f'  ✅ 片段 {i+1} 已转换为 MP4')
                except subprocess.CalledProcessError as e:
                    print(f'  ❌ 片段 {i+1} 转换失败 (退出码 {e.returncode}):')
                    print(f'  === FFmpeg stdout (片段 {i+1}) ===')
                    print(e.stdout if e.stdout else '(无输出)')
                    print(f'  === FFmpeg stderr (片段 {i+1}) ===')
                    print(e.stderr if e.stderr else '(无输出)')
                    print(f'  ================================')

                    # 跳过损坏的片段，继续处理其他片段
                    print(f'  ⚠️ 跳过损坏的片段 {i+1}，继续处理其他片段...')
                    continue

            # 检查是否有有效的 MP4 文件
            if not temp_mp4_files:
                raise Exception('所有视频片段都转换失败，无法继续处理')

            # 创建 ffmpeg concat 文件列表
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
                for mp4_path in temp_mp4_files:
                    concat_file.write(f"file '{mp4_path}'\n")
                concat_file_path = concat_file.name

            print(f'📝 Concat 文件: {concat_file_path}')

            # 合并所有 MP4 文件
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
                output_path = output_file.name

            print('🔄 第二步：合并所有 MP4 文件...')
            subprocess.run([
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file_path,
                '-c', 'copy',  # 直接复制流，不重新编码（更快）
                output_path
            ], check=True, capture_output=True, text=True)

            print(f'✅ 视频合并完成: {output_path}')

            # 读取合并后的 MP4 数据
            with open(output_path, 'rb') as f:
                video_data = f.read()
                video_mime = 'video/mp4'

            print(f'📦 合并后 MP4 大小: {len(video_data)} bytes')

            # 清理临时文件
            for path in temp_webm_files + temp_mp4_files + [concat_file_path, output_path]:
                try:
                    os.unlink(path)
                except:
                    pass

        # 编码为 base64
        video_base64 = base64.b64encode(video_data).decode('utf-8')
        print(f'🔐 Base64 编码长度: {len(video_base64)} 字符')

        # 调用大模型（流式返回）
        print(f'⏳ 调用大模型 {MODEL}...')
        print(f'📊 大模型调用参数:')
        print(f'   - model: {MODEL}')
        print(f'   - video_format: {video_mime}')
        print(f'   - video_size: {len(video_data)} bytes ({len(video_data) / 1024 / 1024:.2f} MB)')
        print(f'   - base64_length: {len(video_base64)} 字符')
        print(f'   - modalities: [text, audio]')
        print(f'   - audio_voice: Cherry')
        print(f'   - audio_format: wav')
        print(f'   - stream: True')

        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'video_url',
                            'video_url': {'url': f'data:{video_mime};base64,{video_base64}'}
                        },
                        {
                            'type': 'text',
                            'text': '请理解这段视频中的内容和问题，并用语音回复我。'
                        }
                    ]
                }
            ],
            modalities=['text', 'audio'],
            audio={'voice': 'Cherry', 'format': 'wav'},
            stream=True,
            stream_options={'include_usage': True}
        )

        print('✅ 开始流式返回音频片段')

        def generate():
            """生成器函数，累积音频后返回较大的片段"""
            text_content = ''
            audio_chunk_count = 0
            pcm_buffer = b''
            MIN_CHUNK_SIZE = 24000  # 24KB (约 0.5 秒音频)

            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta

                    # 收集文本
                    if hasattr(delta, 'content') and delta.content:
                        text_content += delta.content
                        print(f'📝 文本片段: {delta.content}')

                    # 累积音频片段
                    if hasattr(delta, 'audio') and delta.audio:
                        if isinstance(delta.audio, dict) and 'data' in delta.audio:
                            audio_data_chunk = delta.audio['data']

                            # 解码 base64 音频数据并累积到缓冲区
                            pcm_chunk = base64.b64decode(audio_data_chunk)
                            pcm_buffer += pcm_chunk
                            print(f'🔊 累积音频数据: +{len(pcm_chunk)} bytes, 总计: {len(pcm_buffer)} bytes')

                            # 当缓冲区达到最小大小时，返回一个完整的 WAV 块
                            if len(pcm_buffer) >= MIN_CHUNK_SIZE:
                                audio_chunk_count += 1
                                wav_chunk = add_wav_header(pcm_buffer)
                                print(f'✅ 返回音频块 #{audio_chunk_count}: {len(wav_chunk)} bytes')
                                yield wav_chunk
                                pcm_buffer = b''
                else:
                    # 打印使用统计
                    if hasattr(chunk, 'usage') and chunk.usage:
                        print(f'📊 Token 使用: {chunk.usage}')

            # 返回剩余的音频数据
            if pcm_buffer:
                audio_chunk_count += 1
                wav_chunk = add_wav_header(pcm_buffer)
                print(f'✅ 返回最后的音频块 #{audio_chunk_count}: {len(wav_chunk)} bytes')
                yield wav_chunk

            print(f'✅ 流式返回完成')
            print(f'📝 完整文本: {text_content}')
            print(f'🔊 总共返回 {audio_chunk_count} 个音频块')

        # 返回流式响应
        return Response(generate(), mimetype='application/octet-stream')

    except Exception as e:
        print(f'❌ 错误: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    处理视频对话
    接收视频，返回音频
    """
    try:
        print('\n' + '='*80)
        print('🎯 收到对话请求')
        print('='*80)

        # 获取视频
        video_file = request.files.get('video')
        if not video_file:
            return jsonify({'error': '缺少视频文件'}), 400

        # 转换视频格式
        webm_data = video_file.read()
        print(f'📦 WebM 文件大小: {len(webm_data)} bytes')

        mp4_data = convert_webm_to_mp4(webm_data)
        video_base64 = base64.b64encode(mp4_data).decode('utf-8')
        print(f'🔐 Base64 编码长度: {len(video_base64)} 字符')

        # 调用大模型（qwen3-omni-flash 支持视频输入和音频输出）
        # 重要：stream 必须为 True 才能返回音频！
        print(f'⏳ 调用大模型 {MODEL}...')
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'video_url',
                            'video_url': {'url': f'data:video/mp4;base64,{video_base64}'}
                        },
                        {
                            'type': 'text',
                            'text': '请理解这段视频中的内容和问题，并用语音回复我。'
                        }
                    ]
                }
            ],
            modalities=['text', 'audio'],  # 请求音频输出
            audio={'voice': 'Cherry', 'format': 'wav'},  # 使用阿里云支持的声音
            stream=True,  # 必须为 True！
            stream_options={'include_usage': True}
        )

        print('✅ 开始接收流式响应')

        # 收集文本和音频
        text_content = ''
        audio_chunks = []

        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta

                # 收集文本
                if hasattr(delta, 'content') and delta.content:
                    text_content += delta.content
                    print(f'📝 文本片段: {delta.content}')

                # 收集音频（注意：audio 是字典，不是对象）
                if hasattr(delta, 'audio') and delta.audio:
                    # delta.audio 是字典: {'data': 'base64_string'}
                    if isinstance(delta.audio, dict) and 'data' in delta.audio:
                        audio_data_chunk = delta.audio['data']
                        audio_chunks.append(audio_data_chunk)
                        print(f'🔊 收到音频片段: {len(audio_data_chunk)} 字符')
            else:
                # 打印使用统计
                if hasattr(chunk, 'usage') and chunk.usage:
                    print(f'📊 Token 使用: {chunk.usage}')

        print(f'✅ 流式响应接收完成')
        print(f'📝 完整文本: {text_content}')
        print(f'🔊 音频片段数: {len(audio_chunks)}')

        # 合并音频
        audio_data = None
        audio_format = AUDIO_FORMAT
        if audio_chunks:
            # 音频是 base64 编码的，需要解码
            pcm_data = b''.join([base64.b64decode(chunk) for chunk in audio_chunks])
            print(f'🔊 合并后 PCM 音频大小: {len(pcm_data)} bytes')

            # 根据配置选择转换方式
            try:
                if AUDIO_FORMAT == 'mp3':
                    # 方式1: 使用 FFmpeg 转换为 MP3（延迟较高）
                    print('📝 使用 MP3 转换方式')
                    audio_data = convert_pcm_to_mp3(pcm_data)
                    file_ext = 'mp3'
                else:
                    # 方式2: 添加 WAV 文件头（推荐，延迟最低）
                    print('📝 使用 WAV 文件头方式')
                    audio_data = add_wav_header(pcm_data)
                    audio_format = 'wav'
                    file_ext = 'wav'

                # 保存音频到测试目录
                import time
                audio_path = f'test/audios/response_{int(time.time())}.{file_ext}'
                with open(audio_path, 'wb') as f:
                    f.write(audio_data)
                print(f'💾 音频已保存: {audio_path}')
            except Exception as e:
                print(f'⚠️  音频转换失败: {e}')
                import traceback
                traceback.print_exc()
                audio_data = None

        # 如果没有音频，只返回文本
        if not audio_data:
            print('⚠️  未收到音频，只返回文本')
            return jsonify({
                'success': True,
                'text': text_content,
                'hasAudio': False
            })

        # 返回音频（base64）
        return jsonify({
            'success': True,
            'text': text_content,
            'hasAudio': True,
            'audio': base64.b64encode(audio_data).decode('utf-8'),
            'audioFormat': audio_format
        })

    except Exception as e:
        print(f'❌ 错误: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/video-auto-chat-with-tts', methods=['POST'])
def video_auto_chat_with_tts():
    """
    视频理解 + 流式 TTS 合成
    分离式架构：视频理解（纯文本）+ Qwen3-TTS 流式合成
    """
    try:
        print('\n' + '='*80)
        print('🎯 收到视频理解 + 流式 TTS 请求')
        print('='*80)

        # 1. 获取并合并视频片段（复用现有逻辑）
        video_files = request.files.getlist('videos')
        if not video_files:
            return jsonify({'error': '缺少视频文件'}), 400

        print(f'📦 收到 {len(video_files)} 个视频片段')

        # 合并视频（与现有 video_auto_chat 相同的逻辑）
        if len(video_files) == 1:
            print('📹 单个视频片段，转换为 MP4')
            webm_data = video_files[0].read()
            video_data = convert_webm_to_mp4(webm_data)
            video_mime = 'video/mp4'
        else:
            print(f'🔀 多个视频片段，开始合并 {len(video_files)} 个片段')
            temp_webm_files = []
            temp_mp4_files = []

            for i, video_file in enumerate(video_files):
                webm_data = video_file.read()
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                    f.write(webm_data)
                    temp_webm_files.append(f.name)

            # 转换所有 WebM 为 MP4
            for i, webm_path in enumerate(temp_webm_files):
                mp4_path = webm_path.replace('.webm', '.mp4')
                try:
                    subprocess.run([
                        'ffmpeg', '-y', '-i', webm_path,
                        '-vcodec', 'libx264', '-acodec', 'aac',
                        '-preset', 'ultrafast', '-crf', '28',
                        mp4_path
                    ], check=True, capture_output=True, text=True)
                    temp_mp4_files.append(mp4_path)
                except subprocess.CalledProcessError:
                    print(f'  ⚠️ 跳过损坏的片段 {i+1}')
                    continue

            if not temp_mp4_files:
                raise Exception('所有视频片段都转换失败')

            # 创建 concat 文件并合并
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
                for mp4_path in temp_mp4_files:
                    concat_file.write(f"file '{mp4_path}'\n")
                concat_file_path = concat_file.name

            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
                output_path = output_file.name

            subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', concat_file_path, '-c', 'copy', output_path
            ], check=True, capture_output=True, text=True)

            with open(output_path, 'rb') as f:
                video_data = f.read()
                video_mime = 'video/mp4'

            # 清理临时文件
            for path in temp_webm_files + temp_mp4_files + [concat_file_path, output_path]:
                try:
                    os.unlink(path)
                except:
                    pass

        # 2. 视频理解（只获取文本）
        video_base64 = base64.b64encode(video_data).decode('utf-8')

        print('\n' + '='*80)
        print('📤 发送给大模型的完整请求（视频理解）')
        print('='*80)
        print(f'🤖 Model: {MODEL}')
        print(f'📊 Modalities: [text]')
        print(f'📹 Video: {video_mime}, {len(video_data)} bytes ({len(video_data) / 1024 / 1024:.2f} MB)')
        print(f'\n📝 Messages:')
        print(f'  [1] Role: system')
        print(f'      Content (前200字符):')
        print(f'      {system_prompt[:200]}...')
        print(f'      (总长度: {len(system_prompt)} 字符)')
        print(f'  [2] Role: user')
        print(f'      Content: [video] data:{video_mime};base64,...(base64 {len(video_base64)} 字符)')
        print('='*80 + '\n')

        print('⏳ 步骤 1: 调用 Qwen3-Omni-Flash 进行视频理解（纯文本模式）...')

        # 注意：虽然我们可以用 stream=True，但因为需要解析完整 JSON 才能提取 message 和 actions，
        # 所以实际上还是需要等待完整响应。使用 stream=False 更简单直接。
        understanding_response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'video_url',
                            'video_url': {'url': f'data:{video_mime};base64,{video_base64}'}
                        }
                    ]
                }
            ],
            modalities=['text'],  # 只要文本！
            stream=False  # 需要完整 JSON 才能解析 message 和 actions
        )

        text_response = understanding_response.choices[0].message.content
        print(f'📝 AI 文本响应 (前200字符): {text_response[:200]}...')
        print(f'📝 完整响应长度: {len(text_response)} 字符')
        print(f'⏱️  视频理解完成，立即开始 TTS 流式合成...')

        # 尝试解析 JSON（如果 system_prompt 要求返回 JSON）
        tts_text = text_response
        actions = []
        try:
            response_json = json.loads(text_response)
            if 'message' in response_json:
                tts_text = response_json.get('message', text_response)
            if 'actions' in response_json:
                actions = response_json.get('actions', [])
                print(f'📋 解析到的 actions: {actions}')
        except json.JSONDecodeError:
            print('📝 响应不是 JSON 格式，直接使用文本')

        # 3. 流式 TTS 合成
        print(f'\n⏳ 步骤 2: 调用 Qwen3-TTS-Flash 进行流式音频合成...')
        print(f'🎵 TTS 文本 (前100字符): {tts_text[:100]}...')

        def generate_audio_stream():
            """流式生成音频并返回 WAV 数据（累积后添加 WAV header）"""
            try:
                # ✅ 第一步：先发送 JSON 元数据块（包含 actions 和 message）
                metadata = {
                    'type': 'metadata',
                    'message': tts_text,
                    'actions': actions
                }
                metadata_json = json.dumps(metadata, ensure_ascii=False)
                metadata_bytes = metadata_json.encode('utf-8')

                # 发送元数据长度（4字节）+ 元数据内容
                metadata_length = len(metadata_bytes)
                yield metadata_length.to_bytes(4, byteorder='big')  # 长度前缀
                yield metadata_bytes  # JSON 数据

                print(f'📋 已发送元数据块: {len(actions)} 个 actions, 消息长度 {len(tts_text)} 字符')

                # ✅ 第二步：调用 Qwen3-TTS 流式 API 生成音频
                # 注意：Qwen3-TTS 使用 text 参数，不是 messages
                responses = dashscope.MultiModalConversation.call(
                    model="qwen3-tts-flash",
                    text=tts_text,  # ✅ 直接传 text 参数！
                    voice="Cherry",
                    language_type="Chinese",
                    stream=True
                )

                chunk_count = 0
                pcm_buffer = b''
                MIN_CHUNK_SIZE = 24000  # 24KB (约 0.5 秒音频，与旧接口一致)

                for response in responses:
                    if response.status_code == 200:
                        audio = response.output.get('audio', {})
                        if audio and audio.data:
                            # DashScope 返回 base64 编码的 PCM 数据
                            pcm_chunk = base64.b64decode(audio.data)
                            pcm_buffer += pcm_chunk
                            print(f'  🔊 TTS 累积音频: +{len(pcm_chunk)} bytes, 总计: {len(pcm_buffer)} bytes')

                            # 当缓冲区达到最小大小时，返回一个完整的 WAV 块
                            if len(pcm_buffer) >= MIN_CHUNK_SIZE:
                                chunk_count += 1
                                wav_chunk = add_wav_header(pcm_buffer, sample_rate=24000)
                                print(f'  ✅ 返回 TTS 音频块 #{chunk_count}: {len(wav_chunk)} bytes')
                                yield wav_chunk
                                pcm_buffer = b''

                        if response.output.get('finish_reason') == 'stop':
                            print(f'✅ TTS 流式生成完成')
                            break
                    else:
                        print(f'❌ TTS 错误: {response.message}')
                        break

                # 返回剩余的音频数据
                if pcm_buffer:
                    chunk_count += 1
                    wav_chunk = add_wav_header(pcm_buffer, sample_rate=24000)
                    print(f'  ✅ 返回最后的 TTS 音频块 #{chunk_count}: {len(wav_chunk)} bytes')
                    yield wav_chunk

                print(f'🎵 TTS 总共返回 {chunk_count} 个 WAV 音频块')

            except Exception as e:
                print(f'❌ TTS 生成失败: {e}')
                traceback.print_exc()

        # 返回流式数据：先发送元数据块，再发送音频流
        return Response(
            generate_audio_stream(),
            mimetype='application/octet-stream',
            headers={
                'Content-Type': 'application/octet-stream',
                'Cache-Control': 'no-cache'
            }
        )

    except Exception as e:
        print(f'❌ 处理失败: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/system-prompt', methods=['GET'])
def get_system_prompt():
    """获取当前的系统提示词"""
    global system_prompt
    return jsonify({'prompt': system_prompt})


@app.route('/api/system-prompt', methods=['POST'])
def update_system_prompt():
    """更新系统提示词"""
    global system_prompt
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': '缺少 prompt 参数'}), 400

        new_prompt = data['prompt'].strip()
        if not new_prompt:
            return jsonify({'error': '提示词不能为空'}), 400

        system_prompt = new_prompt
        print(f'✅ 系统提示词已更新 (长度: {len(system_prompt)} 字符)')

        return jsonify({'success': True, 'prompt': system_prompt})
    except Exception as e:
        print(f'❌ 更新系统提示词失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/latest-videos', methods=['GET'])
def get_latest_videos():
    """获取最新保存的视频文件信息"""
    global latest_videos

    if not latest_videos['segments'] and not latest_videos['merged']:
        return jsonify({'error': '暂无视频', 'segments': [], 'merged': None})

    result = {
        'segments': [
            {
                'filename': segment['filename'],
                'url': f'/static/videos/{segment["filename"]}',
                'type': segment['type'],
                'original_name': segment['original_name']
            }
            for segment in latest_videos['segments']
        ],
        'merged': {
            'filename': latest_videos['merged'],
            'url': f'/static/videos/{latest_videos["merged"]}'
        } if latest_videos['merged'] else None,
        'timestamp': latest_videos['timestamp']
    }

    return jsonify(result)


if __name__ == '__main__':
    print('🚀 数字人对话系统启动！')
    print(f'📡 访问地址: http://localhost:5001')
    print(f'🤖 使用模型: {MODEL}')
    print(f'🎵 音频格式: {AUDIO_FORMAT.upper()} {"(快速)" if AUDIO_FORMAT == "wav" else "(兼容)"}')
    print(f'💬 系统提示词: 已加载 ({len(system_prompt)} 字符)')

    app.run(host='0.0.0.0', port=5001, debug=True)
