"""
真实 AI 对话测试

测试完整流程：学生信息 + 知识点 + 动态 Prompt + AI 对话 + TTS
"""

import requests
import json

BASE_URL = "http://localhost:5001"


def test_real_chat():
    """测试真实的 AI 对话"""
    print("\n" + "="*80)
    print("🤖 测试真实 AI 对话")
    print("="*80)

    # 发起对话
    print("\n📤 发送请求...")
    print("  - 学生: student_001 (张三)")
    print("  - 话题: eye_contact (眼神交流)")
    print("  - 消息: 你好，我想学习眼神交流技巧")

    response = requests.post(
        f"{BASE_URL}/api/chat",
        data={
            'student_id': 'student_001',
            'session_id': 'real_test_session',
            'topic': 'eye_contact',
            'text': '你好，我想学习眼神交流技巧，请给我一些建议'
        },
        stream=True
    )

    if response.status_code != 200:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)
        return

    print(f"✅ 请求成功，状态码: {response.status_code}")

    # 解析元数据块
    print("\n📥 接收响应...")
    raw_data = response.raw

    try:
        # 读取元数据长度（4字节）
        metadata_length_bytes = raw_data.read(4)
        if len(metadata_length_bytes) < 4:
            print("❌ 未收到完整的元数据长度")
            return

        metadata_length = int.from_bytes(metadata_length_bytes, byteorder='big')
        print(f"📋 元数据长度: {metadata_length} 字节")

        # 读取元数据
        metadata_bytes = raw_data.read(metadata_length)
        metadata = json.loads(metadata_bytes.decode('utf-8'))

        print(f"\n" + "="*80)
        print("📋 元数据内容")
        print("="*80)
        print(f"\n🤖 AI 消息:")
        print(f"{metadata['message']}\n")

        if metadata['actions']:
            print(f"📌 Actions ({len(metadata['actions'])} 个):")
            for i, action in enumerate(metadata['actions'], 1):
                print(f"\n{i}. {action['type'].upper()}")
                # 打印完整的 action 内容（更灵活）
                action_copy = dict(action)
                action_copy.pop('type')
                for key, value in action_copy.items():
                    if isinstance(value, dict):
                        print(f"   {key}:")
                        for k, v in value.items():
                            print(f"     - {k}: {v}")
                    elif isinstance(value, list):
                        print(f"   {key}: {value}")
                    else:
                        print(f"   {key}: {value}")

        print(f"\n" + "="*80)
        print("📊 会话信息")
        print("="*80)
        print(f"会话 ID: {metadata['session_id']}")
        print(f"学生 ID: {metadata['student_id']}")

        # 接收音频流
        print(f"\n" + "="*80)
        print("🔊 音频流信息")
        print("="*80)

        audio_data = raw_data.read()
        audio_size = len(audio_data)

        print(f"音频数据大小: {audio_size} 字节 ({audio_size / 1024:.2f} KB)")

        if audio_size > 0:
            # 保存音频文件
            import os
            os.makedirs('test', exist_ok=True)
            output_path = 'test/real_chat_output.pcm'
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            print(f"✅ 音频已保存到: {output_path}")
            print(f"💡 播放命令: ffplay -f s16le -ar 24000 -ac 1 {output_path}")
        else:
            print("⚠️  未接收到音频数据（可能 TTS 服务未启用）")

        print(f"\n" + "="*80)
        print("✅ 测试完成！")
        print("="*80)

    except Exception as e:
        print(f"\n❌ 解析响应失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_real_chat()
