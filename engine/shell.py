import subprocess
import re
from pathlib import Path
from typing import Dict, Tuple

DANGEROUS_PATTERNS = [
    r'\brm\s+-rf\s+/',
    r'\bdd\s+if=',
    r'\bmkfs\.',
    r'>\s*/dev/',
    r'\bformat\s+[a-z]:',
]


def is_safe_command(command: str) -> Tuple[bool, str]:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"危险命令模式: {pattern}"
    return True, ""


def shell_capability(args: Dict, working_dir: Path) -> Dict:
    command = args.get('command', '')
    
    is_safe, reason = is_safe_command(command)
    if not is_safe:
        return {"error": f"命令被拒绝: {reason}"}
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"error": "命令执行超时（30秒）"}
    except Exception as e:
        return {"error": str(e)}
