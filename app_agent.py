"""
Agent 应用层 - 对外服务接口

提供：
1. 聊天接口（输出：语音 + actions）
2. 学生信息查询接口
3. 知识点查询接口
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
import base64
import os
import tempfile

# 导入内部模块
from multimodal_engine import multimodal_chat, stream_tts
from mock_data import get_student, get_all_students, get_knowledge, get_all_knowledge
from prompt_builder import build_system_prompt

app = Flask(__name__)
CORS(app)

# 对话历史管理（内存存储）
conversation_history = {}  # {session_id: [messages]}
MAX_HISTORY = 20


def get_conversation_history(session_id):
    """获取会话的对话历史"""
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    return conversation_history[session_id]


def add_to_conversation_history(session_id, role, content):
    """添加一条消息到对话历史"""
    if session_id not in conversation_history:
        conversation_history[session_id] = []

    conversation_history[session_id].append({
        'role': role,
        'content': content
    })

    # 限制历史长度
    if len(conversation_history[session_id]) > MAX_HISTORY:
        conversation_history[session_id] = conversation_history[session_id][-MAX_HISTORY:]


# ============================================
# 1. 聊天接口
# ============================================

@app.route('/api/chat', methods=['POST'])
def agent_chat():
    """
    Agent 对话接口（主接口）

    参数:
        - student_id: 学生 ID（必需）
        - session_id: 会话 ID（可选）
        - video: 视频文件（可选）
        - audio: 音频文件（可选）
        - image: 图像文件（可选）
        - text: 文本消息（可选）
        - topic: 当前话题（可选，用于加载特定知识点）

    返回（流式）:
        [4字节长度][元数据 JSON][音频流...]
    """
    try:
        print('\n' + '='*80)
        print('📥 收到 Agent 对话请求')
        print('='*80)

        # 1. 获取参数
        student_id = request.form.get('student_id')
        session_id = request.form.get('session_id', f'session_{os.urandom(4).hex()}')
        topic = request.form.get('topic')  # 可选：指定当前教学知识点

        if not student_id:
            return jsonify({'success': False, 'error': '缺少 student_id 参数'}), 400

        print(f'🔑 学生 ID: {student_id}')
        print(f'🔑 会话 ID: {session_id}')
        print(f'📚 话题: {topic or "无"}')

        # 2. 获取学生信息（动态）
        student = get_student(student_id)
        if not student:
            return jsonify({'success': False, 'error': f'学生 {student_id} 不存在'}), 404

        print(f'👤 学生: {student["name"]} ({student["level"]})')

        # 3. 获取知识点（动态，如果指定了 topic）
        knowledge = None
        if topic:
            knowledge = get_knowledge(topic)
            if knowledge:
                print(f'📖 知识点: {knowledge["title"]}')

        # 4. 动态构建 System Prompt
        system_prompt = build_system_prompt(student, knowledge)
        print(f'📝 System Prompt 长度: {len(system_prompt)} 字符')

        # 5. 获取会话历史
        history = get_conversation_history(session_id)
        print(f'📚 会话历史: {len(history)} 条消息')

        # 6. 处理用户输入（视频/音频/图像/文本）
        user_content = []

        # 视频
        if 'video' in request.files:
            video_file = request.files['video']
            print(f'🎥 收到视频: {video_file.filename}')

            # 读取视频并转为 base64
            video_data = video_file.read()
            video_base64 = base64.b64encode(video_data).decode('utf-8')
            video_mime = video_file.content_type or 'video/webm'

            user_content.append({
                'type': 'video_url',
                'video_url': {'url': f'data:{video_mime};base64,{video_base64}'}
            })

        # 音频
        if 'audio' in request.files:
            audio_file = request.files['audio']
            print(f'🎤 收到音频: {audio_file.filename}')

            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            audio_mime = audio_file.content_type or 'audio/webm'

            user_content.append({
                'type': 'audio_url',
                'audio_url': {'url': f'data:{audio_mime};base64,{audio_base64}'}
            })

        # 图像
        if 'image' in request.files:
            image_file = request.files['image']
            print(f'🖼️  收到图像: {image_file.filename}')

            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_mime = image_file.content_type or 'image/jpeg'

            user_content.append({
                'type': 'image_url',
                'image_url': {'url': f'data:{image_mime};base64,{image_base64}'}
            })

        # 文本
        if 'text' in request.form:
            text = request.form.get('text')
            print(f'💬 收到文本: {text[:50]}...')
            user_content.append({'type': 'text', 'text': text})

        if not user_content:
            return jsonify({'success': False, 'error': '未提供任何输入内容'}), 400

        # 7. 构建完整消息列表
        messages = [
            {'role': 'system', 'content': system_prompt}
        ]

        # 添加历史对话
        messages.extend(history)

        # 添加当前用户输入
        messages.append({
            'role': 'user',
            'content': user_content
        })

        print(f'📨 完整消息列表: {len(messages)} 条')

        # 8. 调用多模态引擎（内部工具）
        print('⏳ 调用多模态引擎进行视频理解...')
        response = multimodal_chat(
            messages=messages,
            modalities=['text'],
            stream=False
        )

        text_response = response.choices[0].message.content
        print(f'✅ AI 响应（前200字符）: {text_response[:200]}...')

        # 9. 解析 JSON 响应（提取 message 和 actions）
        tts_text = text_response
        actions = []

        try:
            response_json = json.loads(text_response)
            if 'message' in response_json:
                tts_text = response_json.get('message', text_response)
            if 'actions' in response_json:
                actions = response_json.get('actions', [])
                print(f'📋 解析到 {len(actions)} 个 actions')
        except json.JSONDecodeError:
            print('📝 响应不是 JSON 格式，直接使用文本')

        # 10. 保存对话历史
        add_to_conversation_history(session_id, 'user', '用户上传了多模态内容')
        add_to_conversation_history(session_id, 'assistant', text_response)
        print(f'💾 已保存对话历史')

        # 11. 流式返回（元数据 + TTS 音频）
        def generate():
            # 第一步：发送元数据块
            metadata = {
                'type': 'metadata',
                'message': tts_text,
                'actions': actions,
                'session_id': session_id,
                'student_id': student_id
            }
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            metadata_bytes = metadata_json.encode('utf-8')

            # 发送元数据长度（4字节）+ 元数据内容
            metadata_length = len(metadata_bytes)
            yield metadata_length.to_bytes(4, byteorder='big')
            yield metadata_bytes

            print(f'📋 已发送元数据块')

            # 第二步：流式 TTS 合成
            print(f'⏳ 开始 TTS 流式合成...')
            try:
                audio_stream = stream_tts(tts_text)
                chunk_count = 0
                for chunk in audio_stream:
                    chunk_count += 1
                    yield chunk
                print(f'✅ TTS 完成，共 {chunk_count} 个音频片段')
            except Exception as e:
                print(f'❌ TTS 失败: {e}')

        return Response(generate(), content_type='application/octet-stream')

    except Exception as e:
        print(f'❌ Agent 对话失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 2. 学生信息查询接口
# ============================================

@app.route('/api/student/<student_id>', methods=['GET'])
def get_student_info(student_id):
    """
    获取学生信息

    参数:
        student_id: 学生 ID

    返回:
        {
            "success": true,
            "student": {...}
        }
    """
    student = get_student(student_id)
    if not student:
        return jsonify({'success': False, 'error': f'学生 {student_id} 不存在'}), 404

    return jsonify({'success': True, 'student': student})


# ============================================
# 3. 知识点查询接口
# ============================================

@app.route('/api/knowledge', methods=['GET'])
def get_knowledge_list():
    """
    获取知识点列表

    参数:
        category: 分类（可选）

    返回:
        {
            "success": true,
            "total": 3,
            "items": [...]
        }
    """
    category = request.args.get('category')
    items = get_all_knowledge(category)

    return jsonify({
        'success': True,
        'total': len(items),
        'items': items
    })


@app.route('/api/knowledge/<topic>', methods=['GET'])
def get_knowledge_detail(topic):
    """
    获取知识点详情

    参数:
        topic: 知识点标识

    返回:
        {
            "success": true,
            "knowledge": {...}
        }
    """
    knowledge = get_knowledge(topic)
    if not knowledge:
        return jsonify({'success': False, 'error': f'知识点 {topic} 不存在'}), 404

    return jsonify({'success': True, 'knowledge': knowledge})


# ============================================
# 4. 健康检查
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'version': '1.0.0',
        'services': {
            'multimodal_engine': 'ok',
            'mock_data': 'ok'
        }
    })


# ============================================
# 启动服务
# ============================================

if __name__ == '__main__':
    print('🚀 Agent 应用层启动！')
    print(f'📡 访问地址: http://localhost:5001')
    print(f'📋 对外接口:')
    print(f'   - POST /api/chat           (聊天接口)')
    print(f'   - GET  /api/student/<id>   (学生查询)')
    print(f'   - GET  /api/knowledge      (知识点列表)')
    print(f'   - GET  /api/knowledge/<id> (知识点详情)')
    print(f'   - GET  /api/health         (健康检查)')

    app.run(host='0.0.0.0', port=5001, debug=True)
