"""
Brain - 智能提示词系统

负责生成高质量的系统提示词
参考 Hermes 的分层提示词设计
"""

import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


class Brain:
    """智能大脑 - 提示词生成系统"""
    
    def __init__(self, working_dir: Path, platform_type: str = "cli"):
        self.working_dir = working_dir
        self.platform_type = platform_type
        self._system_prompt_cache = None
        self._project_context_cache = None
    
    def generate(self, capabilities: List[Dict], context: Optional[str] = None) -> str:
        """生成系统提示词 - 分层组合"""
        parts = [
            self._get_core_identity(),
            self._get_environment_info(),
            self._scan_project_context(),
            self._get_capabilities_info(capabilities),
        ]
        
        if context:
            parts.append(f"\n## 任务上下文\n\n{context}")
        
        prompt = "\n".join(part for part in parts if part)
        
        return prompt
    
    def _get_core_identity(self) -> str:
        """核心身份提示词"""
        return """# Omni-Agent - 智能数字员工

你是 Omni-Agent，一个生产级 AI 助手，专注于高效完成任务。

## 核心原则

### 1. 工具使用优先级（重要！）
**必须严格遵守以下优先级顺序：**

1. **专用工具优先** - 文件操作用 read_file/write_file/edit_file
2. **搜索工具次之** - 查找内容用 grep，查找文件用 glob  
3. **Shell 最后使用** - 仅在没有专用工具时才用 shell

**示例：**
- ❌ 错误：`shell("cat file.py")` 
- ✅ 正确：`read_file("file.py")`

- ❌ 错误：`shell("find . -name '*.py'")`
- ✅ 正确：`glob("**/*.py")`

- ❌ 错误：`shell("grep -r 'pattern' .")`
- ✅ 正确：`grep("pattern", ".")`

### 2. 交互式命令处理（重要！）
**当遇到交互式命令时，使用后台进程模式：**

- **后台运行** - 使用 `background: true` 启动后台进程
- **发送输入** - 使用 `process_send_input` 向进程发送输入
- **检查状态** - 使用 `process_poll` 或 `process_read_log` 查看输出

**示例：**
```python
# 启动后台进程
result = shell({"command": "python app.py", "background": true})
session_id = result["session_id"]

# 检查进程状态
process_poll({"session_id": session_id})

# 读取完整日志
process_read_log({"session_id": session_id})

# 向进程发送输入
process_send_input({"session_id": session_id, "data": "yes\\n"})

# 终止进程
process_kill({"session_id": session_id})
```

### 3. 安全第一
- 绝不执行危险操作（rm -rf, format 等）
- 验证所有路径和命令
- 保护敏感信息

### 4. 高效执行
- 直接解决问题，避免不必要的步骤
- 一次性完成任务，减少迭代
- 并行使用多个工具（如果可能）

### 5. 清晰沟通
- 简洁但完整地说明你在做什么
- 解释关键决策
- 报告重要进展和结果

### 6. 代码编写策略（重要！）
**编写代码时必须遵循分模块原则：**

- **分步骤创建** - 不要一次性写完所有代码
- **先基础后功能** - 先创建基础结构，再逐步添加功能
- **一个文件一次** - 每次只创建或修改一个文件
- **测试后继续** - 创建关键文件后，先测试再继续

**示例流程：**
1. 创建项目基础结构（目录、配置文件）
2. 创建数据模型或数据库初始化
3. 创建核心功能模块（一个一个来）
4. 创建 API 路由或接口
5. 创建前端页面（如果需要）
6. 测试和调试

**禁止行为：**
- ❌ 一次性写完整个后端（几百行代码）
- ❌ 同时创建多个复杂文件
- ❌ 不测试就继续添加功能"""
    
    def _get_environment_info(self) -> str:
        """环境信息"""
        now = datetime.now()
        os_info = platform.system()
        
        platform_desc = {
            "cli": "命令行界面（CLI）",
            "telegram": "Telegram 聊天",
            "discord": "Discord 聊天",
            "web": "Web 界面"
        }.get(self.platform_type, "未知平台")
        
        return f"""
## 环境信息

- **当前时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
- **操作系统**: {os_info}
- **工作目录**: {self.working_dir}
- **平台类型**: {platform_desc}
"""
    
    def _scan_project_context(self) -> str:
        """扫描项目上下文（.cursorrules, AGENTS.md 等）"""
        if self._project_context_cache:
            return self._project_context_cache
        
        context_parts = []
        
        context_files = [
            '.cursorrules',
            'AGENTS.md',
            '.agentrc',
            'PROJECT.md',
        ]
        
        for filename in context_files:
            file_path = self.working_dir / filename
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if content.strip():
                        context_parts.append(f"### {filename}\n{content.strip()}")
                except Exception:
                    pass
        
        if context_parts:
            result = "\n## 项目上下文\n\n" + "\n\n".join(context_parts)
            self._project_context_cache = result
            return result
        
        return ""
    
    def _get_capabilities_info(self, capabilities: List[Dict]) -> str:
        """能力信息 - 增强版，包含使用指导"""
        if not capabilities:
            return ""
        
        lines = ["## 可用工具\n"]
        
        tool_categories = {
            "文件操作": ["read_file", "write_file", "edit_file"],
            "搜索工具": ["grep", "glob"],
            "系统工具": ["shell"],
            "进程管理": ["process_poll", "process_wait", "process_read_log", "process_send_input", "process_kill", "process_list"]
        }
        
        for category, tool_names in tool_categories.items():
            category_tools = [cap for cap in capabilities 
                            if cap.get('function', {}).get('name') in tool_names]
            
            if category_tools:
                lines.append(f"\n### {category}")
                for cap in category_tools:
                    func = cap.get('function', {})
                    name = func.get('name', '')
                    desc = func.get('description', '')
                    lines.append(f"- **{name}**: {desc}")
        
        lines.append("\n### 工具使用提示")
        lines.append("- 优先使用专用工具，避免不必要的 shell 命令")
        lines.append("- 文件操作：read_file → edit_file → write_file")
        lines.append("- 搜索操作：grep（内容搜索）、glob（文件名搜索）")
        lines.append("- 批量操作：可以连续调用多个工具")
        lines.append("\n### 后台进程管理")
        lines.append("- **启动后台任务**: shell({\"command\": \"...\", \"background\": true})")
        lines.append("- **检查进度**: process_poll(session_id) 或 process_read_log(session_id)")
        lines.append("- **发送输入**: process_send_input(session_id, \"input\\n\")")
        lines.append("- **等待完成**: process_wait(session_id)")
        lines.append("- **终止进程**: process_kill(session_id)")
        lines.append("- **适用场景**: 长时间运行的服务、需要交互的命令、开发服务器等")
        
        return "\n".join(lines)
