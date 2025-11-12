"""
Mock 数据 - 学生信息和知识点库

用于开发阶段，后续可替换为真实数据库
"""

# Mock 学生数据
MOCK_STUDENTS = {
    'student_001': {
        'student_id': 'student_001',
        'name': '张三',
        'age': 28,
        'level': '初级',
        'background': '企业管理者，需要提升公众演讲能力',
        'goals': [
            '克服紧张情绪',
            '提升表达清晰度',
            '增强肢体语言'
        ],
        'history': {
            'total_sessions': 15,
            'total_duration': 7200,
            'last_session': '2025-11-10T15:30:00Z',
            'strengths': ['声音洪亮', '逻辑清晰'],
            'weaknesses': ['眼神交流不足', '手势僵硬'],
            'progress': {
                'eye_contact': {'score': 6.5, 'trend': '+1.2'},
                'body_language': {'score': 5.8, 'trend': '+0.5'},
                'voice_control': {'score': 8.2, 'trend': '+0.3'}
            }
        }
    },
    'student_002': {
        'student_id': 'student_002',
        'name': '李四',
        'age': 32,
        'level': '中级',
        'background': '销售总监，需要提升谈判和演讲技巧',
        'goals': [
            '提升说服力',
            '掌握高级演讲技巧',
            '增强气场和自信'
        ],
        'history': {
            'total_sessions': 25,
            'total_duration': 12000,
            'last_session': '2025-11-11T10:00:00Z',
            'strengths': ['表达流畅', '逻辑严谨', '手势自然'],
            'weaknesses': ['语速偏快', '互动不足'],
            'progress': {
                'eye_contact': {'score': 8.5, 'trend': '+0.5'},
                'body_language': {'score': 7.8, 'trend': '+0.8'},
                'voice_control': {'score': 7.2, 'trend': '+0.3'}
            }
        }
    }
}


# Mock 知识点库
MOCK_KNOWLEDGE = {
    'eye_contact': {
        'topic': 'eye_contact',
        'title': '眼神交流技巧',
        'description': '如何通过眼神交流增强演讲效果',
        'difficulty': '初级',
        'content': {
            'theory': '''
眼神交流是演讲的重要组成部分，能够：
1. 建立与观众的情感连接
2. 增强说服力和可信度
3. 保持观众注意力
4. 传递自信和真诚

有效的眼神交流不是盯着某个人看，而是自然地与不同观众进行短暂的视线接触。
            '''.strip(),
            'methods': [
                {
                    'name': '3-5秒法则',
                    'description': '与每位观众保持3-5秒的眼神接触',
                    'example': '在演讲时，选择不同区域的观众，依次与他们进行3-5秒的眼神接触，然后自然转移到下一位。'
                },
                {
                    'name': '扫视法',
                    'description': '眼神在观众中自然扫视，形成全场覆盖',
                    'example': '按照Z字形或W字形路径，让眼神覆盖整个观众席，避免遗漏某个区域。'
                },
                {
                    'name': '定点法',
                    'description': '在不同区域选择"锚点观众"进行定期眼神交流',
                    'example': '在前排、中排、后排各选择1-2位观众作为锚点，定期与他们进行眼神交流。'
                }
            ],
            'common_mistakes': [
                '盯着同一个人看太久，让对方感到不适',
                '完全不看观众，只看稿子或天花板',
                '眼神游离不定，显得不自信',
                '只看前排观众，忽略后排',
                '眼神呆滞，缺乏情感'
            ],
            'practice_tips': [
                '每天对着镜子练习5分钟，观察自己的眼神',
                '录制视频回看，检查眼神交流的频率和质量',
                '请朋友给予反馈，了解对方的感受',
                '从小范围观众（3-5人）开始练习，逐步增加',
                '在日常对话中有意识地训练眼神交流'
            ]
        },
        'resources': [
            {
                'type': 'video',
                'url': 'https://cdn.example.com/eye-contact-tutorial.mp4',
                'title': '眼神交流教学视频',
                'duration': 180,
                'description': 'TED 演讲者示范如何进行有效的眼神交流'
            },
            {
                'type': 'image',
                'url': 'https://cdn.example.com/eye-contact-diagram.png',
                'title': '眼神交流示意图',
                'description': '观众席眼神覆盖路径示意图'
            }
        ]
    },
    'body_language': {
        'topic': 'body_language',
        'title': '肢体语言运用',
        'description': '演讲中的手势和姿态技巧',
        'difficulty': '中级',
        'content': {
            'theory': '''
肢体语言占据演讲效果的55%，包括：
1. 手势：强调重点、表达情感
2. 姿态：传递自信和专业形象
3. 移动：增加动态感和互动
4. 面部表情：配合语言内容

自然、得体的肢体语言能够大幅提升演讲感染力。
            '''.strip(),
            'methods': [
                {
                    'name': '开放式手势',
                    'description': '双手自然张开，手心向上或向前',
                    'example': '表达欢迎、诚恳、包容时使用，如"欢迎大家"时双手张开。'
                },
                {
                    'name': '指示性手势',
                    'description': '用手指或手掌指向某个方向',
                    'example': '强调重点、列举事项时使用，如"第一点"、"第二点"配合手势。'
                },
                {
                    'name': '描述性手势',
                    'description': '用手势模拟或描述事物',
                    'example': '描述大小、高低、远近时，用手势辅助表达。'
                }
            ],
            'common_mistakes': [
                '手势僵硬，像机器人',
                '手势过多，让人眼花缭乱',
                '双手插兜或交叉胸前，显得防御或不自信',
                '手势与语言内容不匹配',
                '只有上半身动作，下半身僵硬'
            ],
            'practice_tips': [
                '模仿优秀演讲者的手势',
                '录制视频，观察自己的肢体语言',
                '在日常对话中有意识地使用手势',
                '练习在镜子前演讲，注意姿态',
                '请专业教练给予反馈'
            ]
        },
        'resources': [
            {
                'type': 'video',
                'url': 'https://cdn.example.com/body-language-tutorial.mp4',
                'title': '肢体语言教学视频',
                'duration': 240,
                'description': '奥巴马演讲肢体语言分析'
            }
        ]
    },
    'voice_control': {
        'topic': 'voice_control',
        'title': '声音控制技巧',
        'description': '如何运用声音的高低、快慢、强弱增强演讲效果',
        'difficulty': '中级',
        'content': {
            'theory': '''
声音是演讲的核心工具，包括：
1. 音量：响亮清晰，让所有人听见
2. 语速：快慢结合，张弛有度
3. 语调：高低起伏，富有情感
4. 停顿：适当留白，强调重点

单调的声音会让观众昏昏欲睡，而富有变化的声音能够牢牢抓住注意力。
            '''.strip(),
            'methods': [
                {
                    'name': '音量控制',
                    'description': '根据场地大小和内容重要性调整音量',
                    'example': '关键观点时提高音量，营造紧张感时降低音量。'
                },
                {
                    'name': '语速变化',
                    'description': '重要内容放慢，次要内容加快',
                    'example': '介绍背景时可以稍快，解释核心观点时放慢语速。'
                },
                {
                    'name': '停顿运用',
                    'description': '在关键句子后停顿2-3秒，让观众思考',
                    'example': '"这就是我们的核心理念"（停顿2秒）"它将改变一切"。'
                }
            ],
            'common_mistakes': [
                '全程一个音调，像念经',
                '语速过快，观众跟不上',
                '音量过小，后排听不见',
                '没有停顿，不给观众思考时间',
                '口头禅过多（"嗯"、"啊"、"那个"）'
            ],
            'practice_tips': [
                '录音回听，找出单调和口头禅',
                '练习朗读不同情感的文章',
                '有意识地在日常对话中控制语速',
                '学习播音员和主持人的声音技巧',
                '进行呼吸训练，增强声音力量'
            ]
        },
        'resources': [
            {
                'type': 'audio',
                'url': 'https://cdn.example.com/voice-control-tutorial.mp3',
                'title': '声音控制教学音频',
                'duration': 300,
                'description': '专业配音员讲解声音控制技巧'
            }
        ]
    }
}


# 获取学生信息
def get_student(student_id):
    """获取学生信息"""
    return MOCK_STUDENTS.get(student_id)


# 获取所有学生列表
def get_all_students():
    """获取所有学生列表"""
    return list(MOCK_STUDENTS.values())


# 获取知识点详情
def get_knowledge(topic):
    """获取知识点详情"""
    return MOCK_KNOWLEDGE.get(topic)


# 获取所有知识点列表
def get_all_knowledge(category=None):
    """获取所有知识点列表（简化版）"""
    items = []
    for topic, knowledge in MOCK_KNOWLEDGE.items():
        items.append({
            'id': f'knowledge_{topic}',
            'topic': knowledge['topic'],
            'title': knowledge['title'],
            'description': knowledge['description'],
            'difficulty': knowledge['difficulty']
        })
    return items
