"""
Omni Engine - 简化版主执行引擎

专为开发者构建 Agent 设计的核心引擎
"""

import time
import logging
import uuid
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from .brain import Brain
from .memory import Memory
from .shield import Shield
from .recovery import Recovery
from .client import OPCClient

logger = logging.getLogger(__name__)


class OmniEngine:
    """
    Omni 主引擎 - MVP 版本
    
    核心功能:
    - 任务执行循环
    - 工具调用
    - 错误处理
    """
    
    def __init__(
        self,
        model: str = "gpt-4",
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        stream: bool = True,
        max_iterations: int = 50,
        max_tokens: int = 100000,
        working_dir: Optional[Path] = None,
        enable_shield: bool = True,
        enable_recovery: bool = True,
        quiet: bool = False,
    ):
        self.model = model
        self.provider = provider
        self.max_iterations = max_iterations
        self.working_dir = working_dir or Path.cwd()
        self.quiet = quiet
        self.session_id = str(uuid.uuid4())
        
        self.client = OPCClient(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            stream=stream,
        )
        
        self.brain = Brain(working_dir=self.working_dir)
        self.memory = Memory(max_tokens=max_tokens)
        self.shield = Shield(working_dir=self.working_dir) if enable_shield else None
        self.recovery = Recovery() if enable_recovery else None
        
        self.messages: List[Dict] = []
        self.iteration = 0
        self.start_time = None
        
        logger.info(f"Omni Engine 初始化: {model} @ {provider}")
    
    def execute(
        self,
        task: str,
        capabilities: Optional[List[Dict]] = None,
        context: Optional[Dict] = None,
    ) -> str:
        """执行任务"""
        self._reset()
        
        system_prompt = self.brain.generate(
            capabilities=capabilities or [],
            context=context.get('description') if context else None
        )
        
        self.messages.append({
            "role": "user",
            "content": task
        })
        
        if not self.quiet:
            print(f"\n🚀 Omni Engine 启动")
            print(f"📋 任务: {task[:100]}...")
            print(f"🔧 能力: {len(capabilities or [])} 个")
            print(f"🆔 会话: {self.session_id[:8]}...\n")
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            
            if not self.quiet:
                print(f"\n🔄 迭代 {self.iteration}/{self.max_iterations}")
            
            if self.memory.should_compress(self.messages):
                if not self.quiet:
                    status = self.memory.get_status(self.messages)
                    print(f"🗜️ 压缩上下文: {status['usage_percent']:.1f}% 使用")
                self.messages = self.memory.compress(self.messages)
            
            try:
                response = self._call_model(
                    system_prompt=system_prompt,
                    messages=self.messages,
                    capabilities=capabilities,
                )
                
                if response.get('tool_calls'):
                    self._handle_capability_calls(response)
                    continue
                else:
                    final_response = response.get('content', '')
                    self.messages.append({
                        "role": "assistant",
                        "content": final_response
                    })
                    
                    if not self.quiet:
                        elapsed = time.time() - self.start_time
                        print(f"\n{'='*50}")
                        print(f"📊 执行摘要")
                        print(f"   迭代次数: {self.iteration}")
                        print(f"   工具调用: {self._count_tool_calls()}")
                        print(f"   总用时: {elapsed:.2f}s")
                        print(f"{'='*50}\n")
                    
                    return final_response
                    
            except Exception as e:
                logger.error(f"执行错误: {e}", exc_info=True)
                
                if self.recovery:
                    if not self.quiet:
                        print(f"⚠️ 错误: {e}")
                        print("🔄 尝试恢复...")
                    
                    self.messages.append({
                        "role": "user",
                        "content": f"上一步出错: {str(e)}. 请尝试其他方法。"
                    })
                    continue
                else:
                    raise
        
        return "达到最大迭代次数,任务未完成。"
    
    def _call_model(
        self,
        system_prompt: str,
        messages: List[Dict],
        capabilities: Optional[List[Dict]],
    ) -> Dict:
        """调用模型"""
        if self.recovery:
            return self.recovery.execute(
                lambda: self.client.chat(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=capabilities,
                )
            )
        else:
            return self.client.chat(
                system_prompt=system_prompt,
                messages=messages,
                tools=capabilities,
            )
    
    def _handle_capability_calls(self, response: Dict):
        """处理工具调用"""
        from engine import execute_capability
        
        tool_calls = response.get('tool_calls', [])
        
        self.messages.append({
            "role": "assistant",
            "content": response.get('content') or "",
            "tool_calls": tool_calls
        })
        
        for call in tool_calls:
            capability_name = call['function']['name']
            tool_call_id = call['id']
            
            try:
                args_str = call['function'].get('arguments', '{}')
                if isinstance(args_str, str):
                    args = json.loads(args_str)
                else:
                    args = args_str
            except json.JSONDecodeError as e:
                logger.error(f"参数解析失败: {e}")
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps({"error": f"参数解析失败: {str(e)}"})
                })
                continue
            
            if self.shield:
                is_safe, reason = self.shield.check_capability(
                    capability_name,
                    args
                )
                
                if not is_safe:
                    if not self.quiet:
                        print(f"🛡️ 安全检查失败: {reason}")
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"error": f"安全检查失败: {reason}"})
                    })
                    continue
            
            if not self.quiet:
                print(f"\n⚡ 执行工具: {capability_name}")
                print(f"🆔 调用ID: {tool_call_id}")
                print(f"📝 参数:")
                for k, v in args.items():
                    print(f"   {k}: {v}")
            
            start_time = time.time()
            
            try:
                result = execute_capability(
                    capability_name,
                    args,
                    working_dir=self.working_dir,
                )
                
                elapsed = time.time() - start_time
                
                if not self.quiet:
                    print(f"✅ 完成 (用时: {elapsed:.2f}s)")
                    result_str = json.dumps(result) if isinstance(result, dict) else str(result)
                    print(f"   结果: {result_str[:200]}...")
                
            except Exception as e:
                result = {"error": str(e)}
                if not self.quiet:
                    print(f"❌ 失败: {e}")
            
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result) if isinstance(result, dict) else str(result)
            })
    
    def _reset(self):
        """重置状态"""
        self.messages = []
        self.iteration = 0
        self.start_time = time.time()
    
    def _count_tool_calls(self) -> int:
        """统计工具调用次数"""
        count = 0
        for msg in self.messages:
            if msg.get("role") == "tool":
                count += 1
        return count
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "messages": len(self.messages),
            "tool_calls": self._count_tool_calls(),
            "elapsed_time": time.time() - self.start_time if self.start_time else 0,
        }
