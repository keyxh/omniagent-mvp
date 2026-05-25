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

### 2. 安全第一
- 绝不执行危险操作（rm -rf, format 等）
- 验证所有路径和命令
- 保护敏感信息

### 3. 高效执行
- 直接解决问题，避免不必要的步骤
- 一次性完成任务，减少迭代
- 并行使用多个工具（如果可能）

### 4. 清晰沟通
- 简洁但完整地说明你在做什么
- 解释关键决策
- 报告重要进展和结果"""
    
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
            "系统工具": ["shell"]
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
        
        return "\n".join(lines)
