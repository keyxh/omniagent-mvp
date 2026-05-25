"""
Omni-Agent - 生产级 AI Agent

OPC (OpenAI Platform Compatible) 标准实现
"""

__version__ = "1.0.0"
__author__ = "Omni-Agent Team"

from .engine import OmniEngine
from .brain import Brain
from .memory import Memory
from .shield import Shield
from .recovery import Recovery

__all__ = [
    'OmniEngine',
    'Brain',
    'Memory',
    'Shield',
    'Recovery',
]
