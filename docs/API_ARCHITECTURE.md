# 后端架构与 API 接口设计

## 📐 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      客户端（前端/第三方应用）                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent 应用层                              │
├─────────────────────────────────────────────────────────────┤
│  • 对话接口（输出：语音 + actions）                          │
│  • 动态 Prompt 构建（学生信息 + 知识点库）                    │
│  • 会话管理（多轮对话记忆）                                   │
│  • Actions 生成与解析                                        │
│  • 学生信息管理                                              │
│  • 知识点库管理                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 内部调用
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   多模态引擎层                                │
├─────────────────────────────────────────────────────────────┤
│  • 视频理解（Qwen3-Omni-Flash）                              │
│  • 音频理解（Qwen3-Omni-Flash）                              │
│  • 图像理解（Qwen3-Omni-Flash）                              │
│  • 流式 TTS（Qwen3-TTS-Flash）                               │
│  • 文本对话（Qwen3-Omni-Flash text-only）                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ API 调用
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              阿里云 DashScope API（Qwen 模型）                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 第一层：多模态引擎层

### 职责
- 提供基础的多模态 AI 能力
- 封装阿里云 DashScope API
- 标准化输入输出格式
- 不关心业务逻辑，只提供纯技术能力

### 对外接口

#### 1. 视频理解接口

```http
POST /api/engine/video/understand
Content-Type: multipart/form-data

参数:
- video: 视频文件（webm/mp4）
- prompt: 文本提示词（可选）
- stream: 是否流式返回（默认 false）

返回:
{
  "success": true,
  "result": {
    "type": "text",
    "content": "视频中的人在进行演讲，表情自然..."
  },
  "usage": {
    "input_tokens": 1234,
    "output_tokens": 567
  }
}
```

#### 2. 音频理解接口

```http
POST /api/engine/audio/understand
Content-Type: multipart/form-data

参数:
- audio: 音频文件（wav/mp3/webm）
- prompt: 文本提示词（可选）
- language: 语言（zh/en，默认 zh）

返回:
{
  "success": true,
  "result": {
    "type": "text",
    "content": "用户说：今天天气真好..."
  }
}
```

#### 3. 图像理解接口

```http
POST /api/engine/image/understand
Content-Type: multipart/form-data

参数:
- image: 图像文件（jpg/png）
- prompt: 文本提示词（可选）

返回:
{
  "success": true,
  "result": {
    "type": "text",
    "content": "图片中是一个演讲PPT，标题是..."
  }
}
```

#### 4. 文本对话接口

```http
POST /api/engine/chat
Content-Type: application/json

Body:
{
  "messages": [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
  ],
  "stream": false
}

返回:
{
  "success": true,
  "result": {
    "type": "text",
    "content": "你好！我是 AI 助手..."
  }
}
```

#### 5. 流式 TTS 接口

```http
POST /api/engine/tts/stream
Content-Type: application/json

Body:
{
  "text": "你好，我是数字人",
  "voice": "Cherry",
  "language": "Chinese",
  "format": "pcm"
}

返回:
Content-Type: application/octet-stream
[流式 PCM 音频数据]
```

---

## 🤖 第二层：Agent 应用层

### 职责
- 封装多模态引擎，提供业务场景能力
- 动态构建 System Prompt（学生信息 + 知识点库）
- 管理会话和对话历史
- 解析和生成 actions
- 学生信息和知识点库管理

### 对外接口

### A. 核心对话接口

#### 1. Agent 对话接口（主接口）

```http
POST /api/agent/chat
Content-Type: multipart/form-data

参数:
- student_id: 学生 ID（必需）
- session_id: 会话 ID（可选，不传则自动生成）
- video: 视频文件（可选）
- audio: 音频文件（可选）
- image: 图像文件（可选）
- text: 文本消息（可选）
- topic: 当前话题（可选，用于加载特定知识点）

返回（流式）:
[4字节长度][元数据 JSON][音频流...]

元数据格式:
{
  "type": "metadata",
  "message": "你的演讲很好，但可以改进眼神交流...",
  "actions": [
    {
      "type": "show",
      "content": {
        "type": "video",
        "url": "https://cdn.example.com/eye-contact-tutorial.mp4",
        "title": "眼神交流技巧教学"
      }
    },
    {
      "type": "progress_update",
      "data": {
        "skill": "eye_contact",
        "score": 6.5,
        "improvement": "+1.2",
        "timestamp": "2025-11-12T10:30:00Z"
      }
    },
    {
      "type": "open_self_observation",
      "video_segment": {
        "start": "00:15",
        "end": "00:32",
        "highlight": "注意这里的眼神交流"
      }
    }
  ],
  "session_id": "session_1234567890_abc",
  "student_id": "student_001"
}
```

**Actions 类型说明：**

```javascript
// 1. show - 展示教学内容
{
  "type": "show",
  "content": {
    "type": "video|image|ppt|text",
    "url": "资源 URL",
    "title": "资源标题",
    "description": "资源描述"
  }
}

// 2. progress_update - 更新学习进度
{
  "type": "progress_update",
  "data": {
    "skill": "技能标识",
    "score": 6.5,  // 当前得分
    "improvement": "+1.2",  // 改进幅度
    "timestamp": "时间戳"
  }
}

// 3. progress_query - 查询历史表现
{
  "type": "progress_query",
  "skill": "eye_contact",  // 要查询的技能
  "timerange": "last_7_days"  // 时间范围
}

// 4. open_self_observation - 打开自我观察窗口
{
  "type": "open_self_observation",
  "video_segment": {
    "start": "00:15",
    "end": "00:32",
    "highlight": "注意事项",
    "comparison": {  // 可选：对比视频
      "url": "正确示范视频 URL"
    }
  }
}

// 5. next_exercise - 推荐下一个练习
{
  "type": "next_exercise",
  "exercise": {
    "id": "exercise_001",
    "title": "眼神交流练习",
    "description": "...",
    "duration": 300  // 秒
  }
}

// 6. summarize - 生成总结报告
{
  "type": "summarize",
  "report": {
    "overall_score": 7.5,
    "strengths": ["声音洪亮", "逻辑清晰"],
    "improvements": ["眼神交流", "手势运用"],
    "next_steps": ["练习眼神交流", "学习手势技巧"]
  }
}
```

#### 2. 纯文本对话接口（无多模态）

```http
POST /api/agent/chat/text
Content-Type: application/json

Body:
{
  "student_id": "student_001",
  "session_id": "session_xxx",
  "text": "我应该如何改进我的演讲？",
  "topic": "speech_improvement"
}

返回:
{
  "success": true,
  "message": "根据你之前的练习，我建议你重点关注...",
  "actions": [...],
  "session_id": "session_xxx"
}
```

### B. 学生信息管理接口

#### 3. 获取学生信息

```http
GET /api/agent/student/{student_id}

返回:
{
  "success": true,
  "student": {
    "student_id": "student_001",
    "name": "张三",
    "age": 28,
    "level": "初级",
    "background": "企业管理者，需要提升公众演讲能力",
    "goals": [
      "克服紧张情绪",
      "提升表达清晰度",
      "增强肢体语言"
    ],
    "history": {
      "total_sessions": 15,
      "total_duration": 7200,  // 秒
      "last_session": "2025-11-10T15:30:00Z",
      "strengths": ["声音洪亮", "逻辑清晰"],
      "weaknesses": ["眼神交流不足", "手势僵硬"],
      "progress": {
        "eye_contact": {"score": 6.5, "trend": "+1.2"},
        "body_language": {"score": 5.8, "trend": "+0.5"},
        "voice_control": {"score": 8.2, "trend": "+0.3"}
      }
    },
    "created_at": "2025-10-01T10:00:00Z",
    "updated_at": "2025-11-10T15:30:00Z"
  }
}
```

#### 4. 创建学生

```http
POST /api/agent/student
Content-Type: application/json

Body:
{
  "name": "张三",
  "age": 28,
  "level": "初级",
  "background": "企业管理者",
  "goals": ["克服紧张", "提升表达清晰度"]
}

返回:
{
  "success": true,
  "student_id": "student_001",
  "message": "学生创建成功"
}
```

#### 5. 更新学生信息

```http
PUT /api/agent/student/{student_id}
Content-Type: application/json

Body:
{
  "level": "中级",
  "goals": ["掌握高级演讲技巧"]
}

返回:
{
  "success": true,
  "message": "学生信息更新成功"
}
```

#### 6. 获取学生进度报告

```http
GET /api/agent/student/{student_id}/progress?timerange=last_30_days

返回:
{
  "success": true,
  "student_id": "student_001",
  "timerange": "last_30_days",
  "summary": {
    "total_sessions": 10,
    "total_duration": 3600,
    "average_score": 7.2,
    "improvement_rate": "+15%"
  },
  "skills": {
    "eye_contact": {
      "current_score": 6.5,
      "start_score": 4.0,
      "improvement": "+2.5",
      "trend": "improving",
      "history": [
        {"date": "2025-11-01", "score": 4.0},
        {"date": "2025-11-05", "score": 5.2},
        {"date": "2025-11-10", "score": 6.5}
      ]
    },
    "body_language": {...},
    "voice_control": {...}
  }
}
```

### C. 知识点库管理接口

#### 7. 获取知识点列表

```http
GET /api/agent/knowledge?category=speech_training

返回:
{
  "success": true,
  "category": "speech_training",
  "total": 50,
  "items": [
    {
      "id": "knowledge_001",
      "topic": "eye_contact",
      "title": "眼神交流技巧",
      "description": "如何通过眼神交流增强演讲效果",
      "difficulty": "初级",
      "tags": ["眼神", "交流", "演讲技巧"]
    },
    {
      "id": "knowledge_002",
      "topic": "body_language",
      "title": "肢体语言运用",
      "description": "演讲中的手势和姿态技巧",
      "difficulty": "中级",
      "tags": ["手势", "姿态", "肢体语言"]
    }
  ]
}
```

#### 8. 获取特定知识点详情

```http
GET /api/agent/knowledge/{topic}

返回:
{
  "success": true,
  "knowledge": {
    "id": "knowledge_001",
    "topic": "eye_contact",
    "title": "眼神交流技巧",
    "description": "眼神交流是演讲的重要组成部分...",
    "content": {
      "theory": "眼神交流的理论基础...",
      "methods": [
        {
          "name": "3-5秒法则",
          "description": "与每位观众保持3-5秒的眼神接触",
          "example": "..."
        },
        {
          "name": "扫视法",
          "description": "眼神在观众中自然扫视，形成全场覆盖",
          "example": "..."
        }
      ],
      "common_mistakes": [
        "盯着同一个人看太久",
        "完全不看观众",
        "眼神游离不定"
      ],
      "practice_tips": [
        "每天对着镜子练习",
        "录制视频回看",
        "请朋友给予反馈"
      ]
    },
    "resources": [
      {
        "type": "video",
        "url": "https://cdn.example.com/eye-contact-tutorial.mp4",
        "title": "眼神交流教学视频",
        "duration": 180
      },
      {
        "type": "image",
        "url": "https://cdn.example.com/eye-contact-diagram.png",
        "title": "眼神交流示意图"
      },
      {
        "type": "pdf",
        "url": "https://cdn.example.com/eye-contact-guide.pdf",
        "title": "眼神交流完整指南"
      }
    ],
    "difficulty": "初级",
    "tags": ["眼神", "交流", "演讲技巧"]
  }
}
```

#### 9. 创建知识点

```http
POST /api/agent/knowledge
Content-Type: application/json

Body:
{
  "topic": "voice_control",
  "title": "声音控制技巧",
  "description": "...",
  "content": {...},
  "resources": [...],
  "difficulty": "中级",
  "tags": ["声音", "控制", "演讲技巧"]
}

返回:
{
  "success": true,
  "knowledge_id": "knowledge_050",
  "message": "知识点创建成功"
}
```

#### 10. 更新知识点

```http
PUT /api/agent/knowledge/{topic}
Content-Type: application/json

Body:
{
  "content": {...},
  "resources": [...]
}

返回:
{
  "success": true,
  "message": "知识点更新成功"
}
```

### D. 会话管理接口

#### 11. 获取会话历史

```http
GET /api/agent/conversation/history?session_id=xxx

返回:
{
  "success": true,
  "session_id": "session_xxx",
  "student_id": "student_001",
  "count": 10,
  "history": [
    {
      "role": "user",
      "content": "用户上传了视频片段",
      "timestamp": "2025-11-12T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "你的演讲很好...",
      "actions": [...],
      "timestamp": "2025-11-12T10:00:15Z"
    }
  ]
}
```

#### 12. 清空会话历史

```http
POST /api/agent/conversation/clear
Content-Type: application/json

Body:
{
  "session_id": "session_xxx"
}

返回:
{
  "success": true,
  "message": "会话历史已清空"
}
```

#### 13. 获取所有会话列表

```http
GET /api/agent/conversation/sessions?student_id=student_001

返回:
{
  "success": true,
  "student_id": "student_001",
  "total": 15,
  "sessions": [
    {
      "session_id": "session_001",
      "message_count": 20,
      "start_time": "2025-11-12T10:00:00Z",
      "last_active": "2025-11-12T10:30:00Z",
      "topic": "eye_contact"
    },
    {
      "session_id": "session_002",
      "message_count": 15,
      "start_time": "2025-11-11T14:00:00Z",
      "last_active": "2025-11-11T14:25:00Z",
      "topic": "body_language"
    }
  ]
}
```

### E. 系统管理接口

#### 14. 更新 System Prompt 模板

```http
PUT /api/agent/system-prompt
Content-Type: application/json

Body:
{
  "template": "你是一位专业的卡耐基演讲教练..."
}

返回:
{
  "success": true,
  "message": "系统提示词模板更新成功"
}
```

#### 15. 获取当前 System Prompt 模板

```http
GET /api/agent/system-prompt

返回:
{
  "success": true,
  "template": "你是一位专业的卡耐基演讲教练...",
  "updated_at": "2025-11-10T10:00:00Z"
}
```

#### 16. 健康检查

```http
GET /api/health

返回:
{
  "success": true,
  "status": "healthy",
  "services": {
    "multimodal_engine": "ok",
    "database": "ok",
    "redis": "ok"
  },
  "version": "1.0.0",
  "timestamp": "2025-11-12T10:30:00Z"
}
```

---

## 📊 数据流示例

### 完整对话流程

```
1. 客户端上传视频
   ↓
POST /api/agent/chat
{
  student_id: "student_001",
  session_id: "session_xxx",
  video: [视频文件],
  topic: "eye_contact"
}

2. Agent 应用层处理
   ↓
2.1 获取学生信息
    GET student_info = call_internal('/api/agent/student/student_001')

2.2 获取知识点库
    GET knowledge = call_internal('/api/agent/knowledge/eye_contact')

2.3 获取会话历史
    GET history = get_conversation_history('session_xxx')

2.4 动态构建 System Prompt
    system_prompt = build_prompt(template, student_info, knowledge)

2.5 调用多模态引擎
    POST /api/engine/video/understand
    {
      video: [视频文件],
      prompt: system_prompt + history
    }

2.6 解析 AI 响应，提取 message 和 actions
    response = {"message": "...", "actions": [...]}

2.7 调用 TTS 引擎
    POST /api/engine/tts/stream
    {
      text: response.message
    }

2.8 保存对话历史
    save_conversation_history('session_xxx', user_msg, ai_msg)

2.9 更新学生进度（如果有 progress_update action）
    update_student_progress('student_001', actions)

3. 返回给客户端
   ↓
[元数据块 + 流式音频]
```

---

## 🔐 认证与鉴权（可选，未来实现）

```http
所有接口支持 Bearer Token 认证

Headers:
Authorization: Bearer <token>

错误响应:
{
  "success": false,
  "error": "Unauthorized",
  "message": "Invalid or expired token"
}
```

---

## 📝 错误处理

### 统一错误格式

```json
{
  "success": false,
  "error": "ErrorType",
  "message": "详细错误信息",
  "code": 4001,
  "timestamp": "2025-11-12T10:30:00Z"
}
```

### 错误代码

```
1xxx - 多模态引擎层错误
  1001 - 视频处理失败
  1002 - 音频处理失败
  1003 - TTS 合成失败
  1004 - API 调用失败

2xxx - Agent 应用层错误
  2001 - 学生不存在
  2002 - 会话不存在
  2003 - 知识点不存在
  2004 - Prompt 构建失败

4xxx - 客户端错误
  4000 - 参数错误
  4001 - 未授权
  4003 - 资源不存在
  4029 - 请求过于频繁

5xxx - 服务器错误
  5000 - 内部错误
  5001 - 数据库错误
  5002 - 缓存错误
```

---

## 🚀 部署架构建议

```
┌─────────────────┐
│   Nginx/Caddy   │  (反向代理 + SSL)
└────────┬────────┘
         │
    ┌────┴────┐
    │ Agent   │  (Flask/FastAPI)
    │ 应用层   │  Port: 5001
    └────┬────┘
         │
    ┌────┴────┐
    │ 多模态   │  (Flask/FastAPI)
    │ 引擎层   │  Port: 5002
    └────┬────┘
         │
    ┌────┴────┐
    │ DashScope│
    │   API   │
    └─────────┘

数据存储:
- Redis (会话缓存)
- PostgreSQL (学生信息、知识点库、对话历史)
- MinIO/OSS (视频、音频文件存储)
```

---

## 📋 总结

### 多模态引擎层（5个接口）
1. 视频理解 - `/api/engine/video/understand`
2. 音频理解 - `/api/engine/audio/understand`
3. 图像理解 - `/api/engine/image/understand`
4. 文本对话 - `/api/engine/chat`
5. 流式 TTS - `/api/engine/tts/stream`

### Agent 应用层（16个接口）
**核心对话（2个）:**
1. Agent 对话 - `/api/agent/chat`
2. 纯文本对话 - `/api/agent/chat/text`

**学生管理（4个）:**
3. 获取学生信息 - `GET /api/agent/student/{id}`
4. 创建学生 - `POST /api/agent/student`
5. 更新学生信息 - `PUT /api/agent/student/{id}`
6. 获取进度报告 - `GET /api/agent/student/{id}/progress`

**知识点库（4个）:**
7. 获取知识点列表 - `GET /api/agent/knowledge`
8. 获取知识点详情 - `GET /api/agent/knowledge/{topic}`
9. 创建知识点 - `POST /api/agent/knowledge`
10. 更新知识点 - `PUT /api/agent/knowledge/{topic}`

**会话管理（3个）:**
11. 获取会话历史 - `GET /api/agent/conversation/history`
12. 清空会话历史 - `POST /api/agent/conversation/clear`
13. 获取会话列表 - `GET /api/agent/conversation/sessions`

**系统管理（3个）:**
14. 更新 Prompt 模板 - `PUT /api/agent/system-prompt`
15. 获取 Prompt 模板 - `GET /api/agent/system-prompt`
16. 健康检查 - `GET /api/health`

### Actions 类型（6种）
1. `show` - 展示教学内容
2. `progress_update` - 更新学习进度
3. `progress_query` - 查询历史表现
4. `open_self_observation` - 打开自我观察窗口
5. `next_exercise` - 推荐下一个练习
6. `summarize` - 生成总结报告
