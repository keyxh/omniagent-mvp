"""
Memory - Hermes 风格上下文管理系统

参考 Hermes Agent 的压缩策略实现
"""

import logging
import hashlib
import json
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class Memory:
    """记忆系统 - Hermes 风格"""
    
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.threshold = 0.50  # 50% 触发压缩（参考 Hermes）
        self.tail_budget = 0.20  # 尾部保护 20%
        self.min_context = 64000  # 最低 64k（安全阈值）
        
        if max_tokens < self.min_context:
            logger.warning(f"max_tokens ({max_tokens}) 低于安全阈值 ({self.min_context})")
    
    def should_compress(self, messages: List[Dict]) -> bool:
        """判断是否需要压缩"""
        if len(messages) < 4:
            return False
        
        current = self._estimate_tokens(messages)
        threshold_tokens = int(self.max_tokens * self.threshold)
        
        return current > threshold_tokens
    
    def compress(self, messages: List[Dict]) -> List[Dict]:
        """
        压缩消息历史 - Hermes v3 风格
        
        Phase 1: MD5 去重 + Smart Collapse（零成本）
        Phase 2: 保护头部和尾部
        Phase 3: 生成结构化摘要
        Phase 4: 清理孤立工具调用
        """
        if len(messages) <= 5:
            return messages
        
        # Phase 1: 预处理（零成本）
        messages = self._deduplicate(messages)
        messages = self._smart_collapse(messages)
        
        # Phase 2: 确定边界
        head_count = 1  # 保护第一条用户消息
        tail_budget_tokens = int(self.max_tokens * self.tail_budget)
        tail_count = self._calculate_tail_count(messages, tail_budget_tokens)
        
        if len(messages) <= head_count + tail_count:
            return messages
        
        # 分割消息
        head = messages[:head_count]
        middle = messages[head_count:-tail_count] if tail_count > 0 else messages[head_count:]
        tail = messages[-tail_count:] if tail_count > 0 else []
        
        # Phase 3: 生成摘要
        summary = self._create_structured_summary(middle)
        
        # Phase 4: 清理孤立工具调用
        result = head + [summary] + tail
        result = self._sanitize_tool_pairs(result)
        
        return result
    
    def _deduplicate(self, messages: List[Dict]) -> List[Dict]:
        """MD5 去重 - 相同的 tool result 只保留最新一份"""
        seen = {}
        result = []
        
        for msg in reversed(messages):
            if msg.get('role') == 'tool':
                content = str(msg.get('content', ''))
                md5 = hashlib.md5(content.encode()).hexdigest()
                
                if md5 not in seen:
                    seen[md5] = True
                    result.insert(0, msg)
            else:
                result.insert(0, msg)
        
        return result
    
    def _smart_collapse(self, messages: List[Dict]) -> List[Dict]:
        """Smart Collapse - 工具输出修剪"""
        result = []
        
        for msg in messages:
            if msg.get('role') == 'tool':
                content = str(msg.get('content', ''))
                
                # 如果工具输出超过 1000 字符，进行修剪
                if len(content) > 1000:
                    # 保留前 500 和后 300 字符
                    collapsed = content[:500] + "\n...[已修剪]...\n" + content[-300:]
                    msg = {**msg, 'content': collapsed}
            
            result.append(msg)
        
        return result
    
    def _calculate_tail_count(self, messages: List[Dict], budget_tokens: int) -> int:
        """计算尾部保护消息数"""
        count = 0
        total_tokens = 0
        
        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens([msg])
            if total_tokens + msg_tokens > budget_tokens:
                break
            total_tokens += msg_tokens
            count += 1
        
        return max(count, 2)  # 至少保护 2 条
    
    def _create_structured_summary(self, messages: List[Dict]) -> Dict:
        """创建结构化摘要 - Hermes action-log 风格"""
        actions = []
        files_modified = set()
        errors = []
        
        for msg in messages:
            role = msg.get('role')
            
            if role == 'user':
                content = str(msg.get('content', ''))[:100]
                actions.append(f"用户: {content}")
            
            elif role == 'assistant':
                if msg.get('tool_calls'):
                    for tc in msg['tool_calls']:
                        func_name = tc['function']['name']
                        actions.append(f"✓ {func_name}")
                        
                        # 提取文件名
                        try:
                            args = json.loads(tc['function'].get('arguments', '{}'))
                            if 'file_path' in args:
                                files_modified.add(args['file_path'])
                        except:
                            pass
            
            elif role == 'tool':
                content = str(msg.get('content', ''))
                if 'error' in content.lower() or 'failed' in content.lower():
                    errors.append(content[:100])
        
        # 构建结构化摘要
        summary_parts = ["[历史摘要]"]
        
        if actions:
            summary_parts.append("\n已完成操作:")
            for i, action in enumerate(actions[-10:], 1):  # 最多 10 条
                summary_parts.append(f"{i}. {action}")
        
        if files_modified:
            summary_parts.append(f"\n涉及文件: {', '.join(list(files_modified)[:5])}")
        
        if errors:
            summary_parts.append(f"\n遇到的错误: {errors[0]}")
        
        summary_parts.append("\n[摘要结束]")
        
        return {
            "role": "user",
            "content": "\n".join(summary_parts)
        }
    
    def _sanitize_tool_pairs(self, messages: List[Dict]) -> List[Dict]:
        """清理孤立的工具调用配对"""
        result = []
        tool_call_ids = set()
        
        # 收集所有 tool_call_id
        for msg in messages:
            if msg.get('tool_calls'):
                for tc in msg['tool_calls']:
                    tool_call_ids.add(tc['id'])
        
        # 检查每个 tool result 是否有对应的 tool_call
        valid_tool_ids = set()
        for msg in messages:
            if msg.get('role') == 'tool':
                tool_id = msg.get('tool_call_id')
                if tool_id in tool_call_ids:
                    valid_tool_ids.add(tool_id)
        
        # 过滤消息
        for msg in messages:
            if msg.get('role') == 'tool':
                if msg.get('tool_call_id') in valid_tool_ids:
                    result.append(msg)
            elif msg.get('tool_calls'):
                # 只保留有效的 tool_calls
                valid_calls = [tc for tc in msg['tool_calls'] if tc['id'] in valid_tool_ids]
                if valid_calls:
                    result.append({**msg, 'tool_calls': valid_calls})
            else:
                result.append(msg)
        
        return result
    
    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """估算 token 数 - 更精确的方法"""
        total = 0
        for msg in messages:
            # 基础 token（role + 格式）
            total += 4
            
            content = str(msg.get('content', ''))
            # 中文约 1.5 字符/token，英文约 4 字符/token
            # 保守估计：3 字符/token
            total += len(content) // 3
            
            # 工具调用额外计算
            if msg.get('tool_calls'):
                for tc in msg['tool_calls']:
                    total += 10  # 工具调用开销
                    args = tc['function'].get('arguments', '')
                    if isinstance(args, str):
                        total += len(args) // 3
        
        return total
    
    def get_status(self, messages: List[Dict]) -> Dict:
        """获取状态"""
        current = self._estimate_tokens(messages)
        usage = (current / self.max_tokens) * 100
        
        return {
            "current_tokens": current,
            "max_tokens": self.max_tokens,
            "usage_percent": usage,
            "status": "正常" if usage < 50 else "接近限制" if usage < 75 else "危险",
        }
