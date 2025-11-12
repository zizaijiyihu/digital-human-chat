# 快速开始 - Agent 应用层

## 🚀 启动服务

```bash
# 设置环境变量
export API_KEY="your-dashscope-api-key"
export API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export MODEL="qwen3-omni-flash"

# 启动 Agent 应用
python3 app_agent.py
```

服务将在 `http://localhost:5001` 启动

---

## 📋 对外接口

### 1. 聊天接口（主接口）

```bash
curl -X POST http://localhost:5001/api/chat \
  -F "student_id=student_001" \
  -F "session_id=test_session" \
  -F "topic=eye_contact" \
  -F "video=@video.webm"
```

**参数：**
- `student_id`（必需）：学生 ID
- `session_id`（可选）：会话 ID，不传则自动生成
- `topic`（可选）：当前教学话题（eye_contact/body_language/voice_control）
- `video`/`audio`/`image`/`text`（至少一个）：用户输入

**返回：** 流式数据（元数据块 + 音频流）

**元数据格式：**
```json
{
  "type": "metadata",
  "message": "你的演讲很好...",
  "actions": [
    {
      "type": "show",
      "content": {
        "type": "video",
        "url": "https://cdn.example.com/tutorial.mp4",
        "title": "教学视频"
      }
    },
    {
      "type": "progress_update",
      "data": {
        "skill": "eye_contact",
        "score": 6.5,
        "improvement": "+1.2"
      }
    }
  ],
  "session_id": "test_session",
  "student_id": "student_001"
}
```

---

### 2. 学生信息查询

```bash
curl http://localhost:5001/api/student/student_001
```

**返回：**
```json
{
  "success": true,
  "student": {
    "student_id": "student_001",
    "name": "张三",
    "age": 28,
    "level": "初级",
    "background": "企业管理者",
    "goals": ["克服紧张情绪", "提升表达清晰度"],
    "history": {
      "total_sessions": 15,
      "strengths": ["声音洪亮", "逻辑清晰"],
      "weaknesses": ["眼神交流不足", "手势僵硬"],
      "progress": {
        "eye_contact": {"score": 6.5, "trend": "+1.2"}
      }
    }
  }
}
```

---

### 3. 知识点列表查询

```bash
curl http://localhost:5001/api/knowledge
```

**返回：**
```json
{
  "success": true,
  "total": 3,
  "items": [
    {
      "id": "knowledge_eye_contact",
      "topic": "eye_contact",
      "title": "眼神交流技巧",
      "description": "如何通过眼神交流增强演讲效果",
      "difficulty": "初级"
    }
  ]
}
```

---

### 4. 知识点详情查询

```bash
curl http://localhost:5001/api/knowledge/eye_contact
```

**返回：**
```json
{
  "success": true,
  "knowledge": {
    "topic": "eye_contact",
    "title": "眼神交流技巧",
    "content": {
      "theory": "眼神交流是演讲的重要组成部分...",
      "methods": [
        {
          "name": "3-5秒法则",
          "description": "与每位观众保持3-5秒的眼神接触",
          "example": "..."
        }
      ],
      "common_mistakes": ["盯着同一个人看太久"],
      "practice_tips": ["每天对着镜子练习5分钟"]
    },
    "resources": [
      {
        "type": "video",
        "url": "https://cdn.example.com/tutorial.mp4",
        "title": "教学视频",
        "duration": 180
      }
    ]
  }
}
```

---

### 5. 健康检查

```bash
curl http://localhost:5001/api/health
```

**返回：**
```json
{
  "success": true,
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "multimodal_engine": "ok",
    "mock_data": "ok"
  }
}
```

---

## 🎯 Actions 类型

### 1. show - 展示教学内容
```json
{
  "type": "show",
  "content": {
    "type": "video|image|ppt|text",
    "url": "资源 URL",
    "title": "资源标题"
  }
}
```

### 2. progress_update - 更新学习进度
```json
{
  "type": "progress_update",
  "data": {
    "skill": "eye_contact",
    "score": 6.5,
    "improvement": "+1.2"
  }
}
```

### 3. progress_query - 查询历史表现
```json
{
  "type": "progress_query",
  "skill": "eye_contact",
  "timerange": "last_7_days"
}
```

### 4. open_self_observation - 打开自我观察窗口
```json
{
  "type": "open_self_observation",
  "video_segment": {
    "start": "00:15",
    "end": "00:32",
    "highlight": "注意这里的眼神交流"
  }
}
```

### 5. next_exercise - 推荐下一个练习
```json
{
  "type": "next_exercise",
  "exercise": {
    "id": "exercise_001",
    "title": "眼神交流练习",
    "duration": 300
  }
}
```

### 6. summarize - 生成总结报告
```json
{
  "type": "summarize",
  "report": {
    "overall_score": 7.5,
    "strengths": ["声音洪亮"],
    "improvements": ["眼神交流"],
    "next_steps": ["练习眼神交流技巧"]
  }
}
```

---

## 📚 Mock 数据

### 学生数据
- `student_001` - 张三（初级，企业管理者）
- `student_002` - 李四（中级，销售总监）

### 知识点数据
- `eye_contact` - 眼神交流技巧（初级）
- `body_language` - 肢体语言运用（中级）
- `voice_control` - 声音控制技巧（中级）

---

## 🔧 架构说明

```
客户端
  ↓
┌──────────────────────┐
│  Agent 应用层        │ ← 对外服务（4个接口）
│  • POST /api/chat    │
│  • GET /api/student  │
│  • GET /api/knowledge│
└──────────────────────┘
  ↓ 内部调用
┌──────────────────────┐
│  多模态引擎          │ ← 内部工具（不对外）
│  • multimodal_chat() │
│  • stream_tts()      │
└──────────────────────┘
  ↓
阿里云 DashScope API
```

### 核心模块

1. **app_agent.py** - Agent 应用层（对外服务）
2. **multimodal_engine.py** - 多模态引擎（内部工具）
3. **mock_data.py** - Mock 数据
4. **prompt_builder.py** - 动态 Prompt 构建

---

## 💡 使用示例

### Python 客户端

```python
import requests

# 1. 查询学生信息
response = requests.get('http://localhost:5001/api/student/student_001')
student = response.json()['student']
print(f"学生: {student['name']}, 水平: {student['level']}")

# 2. 查询知识点列表
response = requests.get('http://localhost:5001/api/knowledge')
knowledge_list = response.json()['items']
for item in knowledge_list:
    print(f"- {item['title']} ({item['difficulty']})")

# 3. 发起对话（上传视频）
with open('video.webm', 'rb') as f:
    response = requests.post('http://localhost:5001/api/chat', files={
        'video': f
    }, data={
        'student_id': 'student_001',
        'topic': 'eye_contact'
    }, stream=True)

    # 解析元数据块
    metadata_length = int.from_bytes(response.raw.read(4), byteorder='big')
    metadata_bytes = response.raw.read(metadata_length)
    metadata = json.loads(metadata_bytes.decode('utf-8'))

    print(f"AI 消息: {metadata['message']}")
    print(f"Actions: {metadata['actions']}")

    # 接收音频流
    with open('output.pcm', 'wb') as audio_file:
        for chunk in response.iter_content(chunk_size=8192):
            audio_file.write(chunk)
```

---

## 📖 相关文档

- [后端架构设计](BACKEND_ARCHITECTURE.md) - 完整架构说明
- [API 架构设计](API_ARCHITECTURE.md) - 接口详细文档

---

## ❓ 常见问题

### Q: 如何添加新的学生数据？
A: 编辑 `mock_data.py` 中的 `MOCK_STUDENTS` 字典

### Q: 如何添加新的知识点？
A: 编辑 `mock_data.py` 中的 `MOCK_KNOWLEDGE` 字典

### Q: 如何修改 System Prompt 模板？
A: 编辑 `system_prompt.md` 文件

### Q: 如何切换到真实数据库？
A: 修改 `mock_data.py` 中的 `get_student()` 和 `get_knowledge()` 函数，连接真实数据库

### Q: 如何部署到生产环境？
A: 使用 Gunicorn 或 uWSGI：
```bash
gunicorn -w 4 -b 0.0.0.0:5001 app_agent:app
```
