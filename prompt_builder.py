"""
动态 Prompt 构建服务

根据学生信息和知识点动态构建 System Prompt
"""

import os


# 读取 System Prompt 模板（固定部分）
def load_system_prompt_template():
    """
    加载系统提示词模板

    返回:
        template: 系统提示词模板文本
    """
    template_path = os.path.join(os.path.dirname(__file__), 'system_prompt.md')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


# 构建学生信息部分
def build_student_section(student):
    """
    构建学生信息部分

    参数:
        student: 学生信息字典

    返回:
        student_section: 学生信息文本
    """
    if not student:
        return ""

    student_section = f"""
## 学生信息

- **姓名**: {student['name']}
- **年龄**: {student['age']}
- **水平**: {student['level']}
- **背景**: {student['background']}
- **学习目标**: {', '.join(student['goals'])}

### 历史表现

- **总课时**: {student['history']['total_sessions']} 节
- **总时长**: {student['history']['total_duration']} 秒
- **优势**: {', '.join(student['history']['strengths'])}
- **待改进**: {', '.join(student['history']['weaknesses'])}

### 当前进度

"""

    for skill, data in student['history']['progress'].items():
        student_section += f"- **{skill}**: {data['score']} 分（{data['trend']}）\n"

    return student_section.strip()


# 构建知识点部分
def build_knowledge_section(knowledge):
    """
    构建知识点部分

    参数:
        knowledge: 知识点信息字典

    返回:
        knowledge_section: 知识点文本
    """
    if not knowledge:
        return ""

    knowledge_section = f"""
## 当前教学知识点

### {knowledge['title']}

**难度**: {knowledge['difficulty']}

**理论基础**:
{knowledge['content']['theory']}

**教学方法**:
"""

    for i, method in enumerate(knowledge['content']['methods'], 1):
        knowledge_section += f"""
{i}. **{method['name']}**
   - 描述: {method['description']}
   - 示例: {method['example']}
"""

    knowledge_section += f"""
**常见错误**:
"""
    for mistake in knowledge['content']['common_mistakes']:
        knowledge_section += f"- {mistake}\n"

    knowledge_section += f"""
**练习建议**:
"""
    for tip in knowledge['content']['practice_tips']:
        knowledge_section += f"- {tip}\n"

    return knowledge_section.strip()


# 动态构建完整的 System Prompt
def build_system_prompt(student, knowledge=None):
    """
    动态构建完整的 System Prompt

    参数:
        student: 学生信息字典
        knowledge: 知识点信息字典（可选）

    返回:
        system_prompt: 完整的系统提示词
    """
    # 1. 加载固定模板
    template = load_system_prompt_template()

    # 2. 构建学生信息部分
    student_section = build_student_section(student)

    # 3. 构建知识点部分（如果提供）
    knowledge_section = build_knowledge_section(knowledge) if knowledge else ""

    # 4. 拼接完整 Prompt
    # 在模板中找到合适的位置插入动态内容
    # 假设模板的最后是 "## 响应格式" 或其他固定部分

    # 简单策略：在模板最后添加动态内容
    system_prompt = template + "\n\n" + student_section

    if knowledge_section:
        system_prompt += "\n\n" + knowledge_section

    return system_prompt


# 测试函数
if __name__ == '__main__':
    from mock_data import get_student, get_knowledge

    # 测试学生 001
    student = get_student('student_001')
    knowledge = get_knowledge('eye_contact')

    prompt = build_system_prompt(student, knowledge)
    print("=== 动态构建的 System Prompt ===\n")
    print(prompt)
    print(f"\n\n总长度: {len(prompt)} 字符")
