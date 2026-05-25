import subprocess
import re
from pathlib import Path
from typing import Dict, Tuple
from .process_manager import process_manager

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
    stdin_input = args.get('stdin_input', None)
    background = args.get('background', False)
    
    is_safe, reason = is_safe_command(command)
    if not is_safe:
        return {"error": f"命令被拒绝: {reason}"}
    
    if background:
        session = process_manager.spawn(command, cwd=str(working_dir))
        return {
            "session_id": session.id,
            "pid": session.pid,
            "message": f"后台任务已启动: {session.id}",
            "success": True
        }
    
    try:
        if stdin_input is not None:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(working_dir),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            try:
                stdout, stderr = process.communicate(input=stdin_input, timeout=30)
                return {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": process.returncode,
                    "success": process.returncode == 0
                }
            except subprocess.TimeoutExpired:
                process.kill()
                return {"error": "命令执行超时（30秒）"}
        else:
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


def process_poll_capability(args: Dict, working_dir: Path) -> Dict:
    session_id = args.get('session_id', '')
    return process_manager.poll(session_id)


def process_wait_capability(args: Dict, working_dir: Path) -> Dict:
    session_id = args.get('session_id', '')
    timeout = args.get('timeout', 180)
    return process_manager.wait(session_id, timeout)


def process_read_log_capability(args: Dict, working_dir: Path) -> Dict:
    session_id = args.get('session_id', '')
    limit = args.get('limit', 200)
    return process_manager.read_log(session_id, limit)


def process_send_input_capability(args: Dict, working_dir: Path) -> Dict:
    session_id = args.get('session_id', '')
    data = args.get('data', '')
    return process_manager.submit_stdin(session_id, data)


def process_kill_capability(args: Dict, working_dir: Path) -> Dict:
    session_id = args.get('session_id', '')
    return process_manager.kill(session_id)


def process_list_capability(args: Dict, working_dir: Path) -> Dict:
    sessions = process_manager.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}
