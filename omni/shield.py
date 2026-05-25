"""
Shield - 安全防护系统

保护系统免受恶意操作
"""

import re
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class Shield:
    """安全防护"""
    
    DANGEROUS_PATTERNS = [
        r'\brm\s+-rf\s+/',
        r'\bdd\s+if=',
        r'\bmkfs\.',
        r'>\s*/dev/',
    ]
    
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.audit_log = []
    
    def check_capability(
        self,
        capability_name: str,
        args: dict
    ) -> Tuple[bool, Optional[str]]:
        """检查能力调用安全性"""
        
        # Shell 命令检查
        if capability_name == 'shell':
            command = args.get('command', '')
            return self._check_command(command)
        
        # 文件操作检查
        if capability_name in ['write_file', 'delete_file']:
            path = args.get('path', '')
            return self._check_path(path)
        
        return True, None
    
    def _check_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """检查命令安全性"""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                self._log_event("BLOCKED_COMMAND", command)
                return False, f"危险命令: {pattern}"
        
        return True, None
    
    def _check_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """检查路径安全性"""
        try:
            full_path = Path(path).resolve()
            working_dir_resolved = self.working_dir.resolve()
            
            # 检查是否在工作目录内
            try:
                full_path.relative_to(working_dir_resolved)
            except ValueError:
                return False, "路径在工作目录外"
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _log_event(self, event_type: str, details: str):
        """记录安全事件"""
        self.audit_log.append({
            "type": event_type,
            "details": details
        })
        logger.warning(f"[Shield] {event_type}: {details}")
