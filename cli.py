#!/usr/bin/env python3
"""
OmniAgent MVP CLI - 最小可执行版本

只包含核心功能和内部工具注册
"""

import sys
import os
import argparse
from pathlib import Path

from omni import OmniEngine
from engine import get_capabilities


def main():
    parser = argparse.ArgumentParser(description='OmniAgent MVP CLI')
    parser.add_argument('--provider', default='openai', help='LLM 提供商 (openai/anthropic)')
    parser.add_argument('--model', default='gpt-4', help='模型名称')
    parser.add_argument('--base-url', help='API 基础 URL (可选)')
    parser.add_argument('--api-key', help='API 密钥')
    parser.add_argument('--max-iterations', type=int, default=50, help='最大迭代次数')
    parser.add_argument('--max-tokens', type=int, default=100000, help='模型最大上下文长度 (默认: 100k)')
    parser.add_argument('task', nargs='?', help='要执行的任务')
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    if args.base_url and not api_key:
        api_key = "dummy-key-for-local-model"
    
    if not api_key:
        print("错误: 未设置 API Key")
        print("请设置环境变量: OPENAI_API_KEY 或 ANTHROPIC_API_KEY")
        print("或使用 --api-key 参数指定")
        print("或使用 --base-url 指定本地模型地址")
        return 1
    
    print("\n" + "="*70)
    print("🤖 OmniAgent MVP CLI")
    print("="*70)
    print(f"\n模型: {args.model}")
    print(f"提供商: {args.provider}")
    if args.base_url:
        print(f"URL: {args.base_url}")
    print()
    
    capabilities = get_capabilities()
    print(f"✓ 已加载 {len(capabilities)} 个内部工具")
    
    engine = OmniEngine(
        provider=args.provider,
        model=args.model,
        api_key=api_key,
        base_url=args.base_url,
        stream=True,
        max_iterations=args.max_iterations,
        max_tokens=args.max_tokens,
        working_dir=Path.cwd(),
        enable_shield=True,
        enable_recovery=True,
        quiet=False,
    )
    
    if args.task:
        print(f"\n执行任务: {args.task}\n")
        try:
            result = engine.execute(args.task, capabilities=capabilities)
            print(f"\n{'='*70}")
            print("✅ 任务完成")
            print(f"{'='*70}\n")
            return 0
        except KeyboardInterrupt:
            print("\n\n⛔ 用户中断")
            return 1
        except Exception as e:
            print(f"\n\n❌ 错误: {e}")
            return 1
    else:
        print("交互模式")
        print("输入任务开始对话，输入 'exit' 或 'quit' 退出\n")
        
        while True:
            try:
                task = input(">>> ").strip()
                
                if not task:
                    continue
                
                if task.lower() in ['exit', 'quit', 'q']:
                    print("\n再见！")
                    break
                
                print()
                result = engine.execute(task, capabilities=capabilities)
                print(f"\n{'='*70}\n")
                
            except KeyboardInterrupt:
                print("\n\n⛔ 用户中断")
                break
            except EOFError:
                print("\n\n再见！")
                break
            except Exception as e:
                print(f"\n\n❌ 错误: {e}\n")
                continue
        
        return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
