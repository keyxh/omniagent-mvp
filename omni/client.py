"""
OPC Client - OpenAI Platform Compatible 客户端

统一的 API 客户端,兼容所有 OpenAI 格式的提供商
"""

import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class OPCClient:
    """
    OPC 客户端
    
    支持所有兼容 OpenAI API 的提供商:
    - OpenAI
    - Anthropic (通过适配器)
    - Azure OpenAI
    - OpenRouter
    - 本地模型 (vLLM, Ollama等)
    """
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = True,
        max_tokens: int = 8192,
    ):
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.stream = stream
        self.max_tokens = max_tokens
        
        # 获取 API Key
        self.api_key = api_key or self._get_api_key()
        
        # 初始化客户端
        if self.provider == "anthropic":
            self._init_anthropic()
        else:
            self._init_openai_compatible(base_url)
    
    def _get_api_key(self) -> str:
        """获取 API Key"""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "azure": "AZURE_OPENAI_KEY",
        }
        
        env_var = key_map.get(self.provider, "API_KEY")
        api_key = os.getenv(env_var)
        
        if not api_key:
            raise ValueError(f"未找到 API Key: {env_var}")
        
        return api_key
    
    def _init_openai_compatible(self, base_url: Optional[str]):
        """初始化 OpenAI 兼容客户端"""
        from openai import OpenAI
        import httpx
        
        http_client = httpx.Client(
            proxies=None,
            transport=httpx.HTTPTransport(retries=3),
        )
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            http_client=http_client,
        )
        logger.info(f"OPC 客户端初始化: {self.provider}")
    
    def _init_anthropic(self):
        """初始化 Anthropic 客户端"""
        from anthropic import Anthropic
        
        self.client = Anthropic(api_key=self.api_key)
        logger.info("Anthropic 客户端初始化")
    
    def chat(
        self,
        system_prompt: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        统一的聊天接口
        
        Returns:
            {"content": str, "tool_calls": [...]}
        """
        if self.provider == "anthropic":
            return self._chat_anthropic(system_prompt, messages, tools)
        else:
            return self._chat_openai(system_prompt, messages, tools)
    
    def _chat_openai(
        self,
        system_prompt: str,
        messages: List[Dict],
        tools: Optional[List[Dict]],
    ) -> Dict:
        """OpenAI 格式调用"""
        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)
        
        kwargs = {
            "model": self.model,
            "messages": api_messages,
            "temperature": self.temperature,
            "stream": self.stream,
            "max_tokens": self.max_tokens,
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        response = self.client.chat.completions.create(**kwargs)
        
        if self.stream:
            return self._handle_stream(response)
        else:
            message = response.choices[0].message
            
            result = {
                "content": message.content or "",
                "tool_calls": None,
            }
            
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ]
            
            return result
    
    def _handle_stream(self, stream):
        """处理流式响应"""
        import sys
        content = ""
        reasoning_content = ""
        tool_calls = []
        tool_call_started = False
        
        for chunk in stream:
            if not chunk.choices:
                continue
                
            delta = chunk.choices[0].delta
            
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                reasoning_content += delta.reasoning_content
            
            if delta.content:
                content += delta.content
                print(delta.content, end="", flush=True)
            
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index >= len(tool_calls):
                        tool_calls.append({
                            "id": tc.id or "",
                            "type": "function",
                            "function": {
                                "name": tc.function.name or "",
                                "arguments": tc.function.arguments or "",
                            }
                        })
                        if not tool_call_started:
                            print("\n🔧 ", end="", flush=True)
                            tool_call_started = True
                    else:
                        if tc.function.name:
                            tool_calls[tc.index]["function"]["name"] += tc.function.name
                            print(tc.function.name, end="", flush=True)
                        if tc.function.arguments:
                            tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments
                            print(tc.function.arguments, end="", flush=True)
        
        if content:
            print()
        if tool_call_started:
            print()
        
        result = {
            "content": content,
            "tool_calls": tool_calls if tool_calls else None,
        }
        
        if reasoning_content:
            result["reasoning_content"] = reasoning_content
        
        return result
    
    def _chat_anthropic(
        self,
        system_prompt: str,
        messages: List[Dict],
        tools: Optional[List[Dict]],
    ) -> Dict:
        """Anthropic 格式调用"""
        # 转换消息格式
        api_messages = []
        for msg in messages:
            if msg["role"] == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg["content"],
                    }]
                })
            else:
                api_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        kwargs = {
            "model": self.model,
            "system": system_prompt,
            "messages": api_messages,
            "temperature": self.temperature,
            "max_tokens": 4096,
        }
        
        if tools:
            kwargs["tools"] = self._convert_tools_anthropic(tools)
        
        response = self.client.messages.create(**kwargs)
        
        result = {
            "content": "",
            "tool_calls": None,
        }
        
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": block.input,
                    }
                })
        
        if tool_calls:
            result["tool_calls"] = tool_calls
        
        return result
    
    def _convert_tools_anthropic(self, tools: List[Dict]) -> List[Dict]:
        """转换工具格式为 Anthropic 格式"""
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"].get("description", ""),
                "input_schema": tool["function"].get("parameters", {}),
            }
            for tool in tools
        ]
