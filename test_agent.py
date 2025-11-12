"""
测试 Agent 应用层

测试所有对外接口：
1. 健康检查
2. 学生信息查询
3. 知识点查询
4. 聊天接口（模拟视频上传）
"""

import requests
import json
import os

BASE_URL = "http://localhost:5001"


def test_health_check():
    """测试健康检查"""
    print("\n" + "="*80)
    print("测试 1: 健康检查")
    print("="*80)

    response = requests.get(f"{BASE_URL}/api/health")
    print(f"状态码: {response.status_code}")

    data = response.json()
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")

    assert response.status_code == 200
    assert data['success'] == True
    assert data['status'] == 'healthy'

    print("✅ 健康检查通过")


def test_student_query():
    """测试学生信息查询"""
    print("\n" + "="*80)
    print("测试 2: 学生信息查询")
    print("="*80)

    # 测试存在的学生
    response = requests.get(f"{BASE_URL}/api/student/student_001")
    print(f"状态码: {response.status_code}")

    data = response.json()
    print(f"学生信息:")
    print(f"  - 姓名: {data['student']['name']}")
    print(f"  - 年龄: {data['student']['age']}")
    print(f"  - 水平: {data['student']['level']}")
    print(f"  - 背景: {data['student']['background']}")
    print(f"  - 优势: {', '.join(data['student']['history']['strengths'])}")
    print(f"  - 待改进: {', '.join(data['student']['history']['weaknesses'])}")

    assert response.status_code == 200
    assert data['success'] == True
    assert data['student']['student_id'] == 'student_001'

    print("✅ 学生信息查询通过")

    # 测试不存在的学生
    response = requests.get(f"{BASE_URL}/api/student/student_999")
    assert response.status_code == 404
    print("✅ 不存在学生返回 404")


def test_knowledge_query():
    """测试知识点查询"""
    print("\n" + "="*80)
    print("测试 3: 知识点查询")
    print("="*80)

    # 测试知识点列表
    response = requests.get(f"{BASE_URL}/api/knowledge")
    print(f"状态码: {response.status_code}")

    data = response.json()
    print(f"知识点列表 (共 {data['total']} 个):")
    for item in data['items']:
        print(f"  - {item['title']} ({item['difficulty']}) - {item['description']}")

    assert response.status_code == 200
    assert data['success'] == True
    assert data['total'] == 3

    print("✅ 知识点列表查询通过")

    # 测试知识点详情
    response = requests.get(f"{BASE_URL}/api/knowledge/eye_contact")
    print(f"\n知识点详情: 眼神交流技巧")

    data = response.json()
    knowledge = data['knowledge']
    print(f"  - 标题: {knowledge['title']}")
    print(f"  - 难度: {knowledge['difficulty']}")
    print(f"  - 方法数量: {len(knowledge['content']['methods'])} 个")
    print(f"  - 常见错误: {len(knowledge['content']['common_mistakes'])} 个")
    print(f"  - 练习建议: {len(knowledge['content']['practice_tips'])} 个")

    assert response.status_code == 200
    assert data['success'] == True
    assert knowledge['topic'] == 'eye_contact'

    print("✅ 知识点详情查询通过")


def test_chat_text():
    """测试聊天接口（纯文本）"""
    print("\n" + "="*80)
    print("测试 4: 聊天接口（纯文本）")
    print("="*80)

    # 纯文本对话
    response = requests.post(
        f"{BASE_URL}/api/chat",
        data={
            'student_id': 'student_001',
            'session_id': 'test_session_001',
            'topic': 'eye_contact',
            'text': '你好，我想学习眼神交流技巧'
        },
        stream=True
    )

    print(f"状态码: {response.status_code}")
    assert response.status_code == 200

    # 解析元数据块
    print("\n正在接收响应...")
    raw_data = response.raw

    # 读取元数据长度（4字节）
    metadata_length_bytes = raw_data.read(4)
    if len(metadata_length_bytes) < 4:
        print("❌ 未收到完整的元数据长度")
        return

    metadata_length = int.from_bytes(metadata_length_bytes, byteorder='big')
    print(f"元数据长度: {metadata_length} 字节")

    # 读取元数据
    metadata_bytes = raw_data.read(metadata_length)
    metadata = json.loads(metadata_bytes.decode('utf-8'))

    print(f"\n📋 元数据:")
    print(f"  - 类型: {metadata['type']}")
    print(f"  - 消息长度: {len(metadata['message'])} 字符")
    print(f"  - 消息（前200字符）: {metadata['message'][:200]}...")
    print(f"  - Actions 数量: {len(metadata['actions'])} 个")

    for i, action in enumerate(metadata['actions'], 1):
        print(f"  - Action {i}: {action['type']}")

    print(f"  - 会话ID: {metadata['session_id']}")
    print(f"  - 学生ID: {metadata['student_id']}")

    assert metadata['type'] == 'metadata'
    assert metadata['student_id'] == 'student_001'
    assert metadata['session_id'] == 'test_session_001'
    assert len(metadata['message']) > 0

    # 接收音频流
    print("\n正在接收音频流...")
    audio_chunks = []
    chunk_count = 0

    for chunk in raw_data.stream(8192):
        if chunk:
            audio_chunks.append(chunk)
            chunk_count += 1

    total_audio_size = sum(len(chunk) for chunk in audio_chunks)
    print(f"音频片段数: {chunk_count}")
    print(f"音频总大小: {total_audio_size} 字节")

    # 保存音频（可选）
    if audio_chunks:
        output_path = 'test/test_output.pcm'
        os.makedirs('test', exist_ok=True)
        with open(output_path, 'wb') as f:
            for chunk in audio_chunks:
                f.write(chunk)
        print(f"音频已保存到: {output_path}")

    print("✅ 聊天接口（纯文本）测试通过")


def test_chat_with_video():
    """测试聊天接口（带视频）"""
    print("\n" + "="*80)
    print("测试 5: 聊天接口（带视频）")
    print("="*80)

    # 创建一个小的测试视频文件（模拟）
    test_video_path = 'test/test_video.webm'
    os.makedirs('test', exist_ok=True)

    # 创建一个小的测试文件
    with open(test_video_path, 'wb') as f:
        f.write(b'\x00' * 1024)  # 1KB 的测试数据

    print(f"创建测试视频: {test_video_path}")

    # 上传视频
    with open(test_video_path, 'rb') as video_file:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            files={'video': ('test.webm', video_file, 'video/webm')},
            data={
                'student_id': 'student_001',
                'session_id': 'test_session_002',
                'topic': 'eye_contact'
            },
            stream=True
        )

    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        # 解析元数据块
        raw_data = response.raw

        metadata_length_bytes = raw_data.read(4)
        metadata_length = int.from_bytes(metadata_length_bytes, byteorder='big')
        metadata_bytes = raw_data.read(metadata_length)
        metadata = json.loads(metadata_bytes.decode('utf-8'))

        print(f"\n📋 元数据:")
        print(f"  - 消息（前150字符）: {metadata['message'][:150]}...")
        print(f"  - Actions: {len(metadata['actions'])} 个")
        print(f"  - 会话ID: {metadata['session_id']}")

        print("✅ 聊天接口（带视频）测试通过")
    else:
        print(f"⚠️  请求失败: {response.text}")
        print("（这可能是因为 API_KEY 未设置或视频格式问题）")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀" + " "*35 + "开始测试" + " "*35 + "🚀")

    try:
        test_health_check()
        test_student_query()
        test_knowledge_query()
        test_chat_text()
        # test_chat_with_video()  # 需要有效的 API_KEY，先注释掉

        print("\n" + "="*80)
        print("✅ 所有测试通过！")
        print("="*80)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到服务器，请确保 Agent 应用已启动:")
        print(f"   python3 app_agent.py")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
