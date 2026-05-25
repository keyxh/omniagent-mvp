import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


MAX_OUTPUT_CHARS = 200_000


@dataclass
class ProcessSession:
    id: str
    command: str
    cwd: str
    started_at: float
    process: Optional[subprocess.Popen] = None
    pid: Optional[int] = None
    exited: bool = False
    exit_code: Optional[int] = None
    output_buffer: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _reader_thread: Optional[threading.Thread] = None


class ProcessManager:
    def __init__(self):
        self._running: Dict[str, ProcessSession] = {}
        self._finished: Dict[str, ProcessSession] = {}
        self._lock = threading.Lock()
    
    def spawn(self, command: str, cwd: str = None) -> ProcessSession:
        if cwd is None:
            cwd = os.getcwd()
        
        session = ProcessSession(
            id=f"proc_{uuid.uuid4().hex[:12]}",
            command=command,
            cwd=str(Path(cwd).resolve()),
            started_at=time.time(),
        )
        
        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=session.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            
            session.process = proc
            session.pid = proc.pid
            
            reader = threading.Thread(
                target=self._reader_loop,
                args=(session,),
                daemon=True,
                name=f"proc-reader-{session.id}",
            )
            session._reader_thread = reader
            reader.start()
            
            with self._lock:
                self._running[session.id] = session
            
            return session
        
        except Exception as e:
            session.exited = True
            session.exit_code = -1
            session.output_buffer = f"Failed to start: {e}"
            with self._lock:
                self._finished[session.id] = session
            return session
    
    def _reader_loop(self, session: ProcessSession):
        try:
            while True:
                chunk = session.process.stdout.read(4096)
                if not chunk:
                    break
                
                with session._lock:
                    session.output_buffer += chunk
                    if len(session.output_buffer) > MAX_OUTPUT_CHARS:
                        session.output_buffer = session.output_buffer[-MAX_OUTPUT_CHARS:]
        
        except Exception:
            pass
        
        finally:
            try:
                session.process.wait(timeout=5)
            except Exception:
                pass
            
            session.exited = True
            session.exit_code = session.process.returncode
            self._move_to_finished(session)
    
    def _move_to_finished(self, session: ProcessSession):
        with self._lock:
            if session.id in self._running:
                del self._running[session.id]
            self._finished[session.id] = session
    
    def get(self, session_id: str) -> Optional[ProcessSession]:
        with self._lock:
            return self._running.get(session_id) or self._finished.get(session_id)
    
    def poll(self, session_id: str) -> dict:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}
        
        with session._lock:
            output_preview = session.output_buffer[-1000:] if session.output_buffer else ""
        
        result = {
            "session_id": session.id,
            "command": session.command,
            "status": "exited" if session.exited else "running",
            "pid": session.pid,
            "uptime_seconds": int(time.time() - session.started_at),
            "output_preview": output_preview,
        }
        
        if session.exited:
            result["exit_code"] = session.exit_code
        
        return result
    
    def read_log(self, session_id: str, limit: int = 200) -> dict:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}
        
        with session._lock:
            full_output = session.output_buffer
        
        lines = full_output.splitlines()
        total_lines = len(lines)
        selected = lines[-limit:] if limit > 0 else lines
        
        return {
            "session_id": session.id,
            "status": "exited" if session.exited else "running",
            "output": "\n".join(selected),
            "total_lines": total_lines,
            "showing": f"{len(selected)} lines",
        }
    
    def wait(self, session_id: str, timeout: int = 180) -> dict:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}
        
        deadline = time.monotonic() + timeout
        
        while time.monotonic() < deadline:
            if session.exited:
                return {
                    "status": "exited",
                    "exit_code": session.exit_code,
                    "output": session.output_buffer[-2000:],
                }
            time.sleep(1)
        
        return {
            "status": "timeout",
            "output": session.output_buffer[-1000:],
            "note": f"Waited {timeout}s, process still running",
        }
    
    def write_stdin(self, session_id: str, data: str) -> dict:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}
        
        if session.exited:
            return {"status": "already_exited", "error": "Process has already finished"}
        
        if not session.process or not session.process.stdin:
            return {"status": "error", "error": "Process stdin not available"}
        
        try:
            session.process.stdin.write(data)
            session.process.stdin.flush()
            return {"status": "ok", "bytes_written": len(data)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def submit_stdin(self, session_id: str, data: str = "") -> dict:
        return self.write_stdin(session_id, data + "\n")
    
    def close_stdin(self, session_id: str) -> dict:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}
        
        if session.exited:
            return {"status": "already_exited", "error": "Process has already finished"}
        
        if not session.process or not session.process.stdin:
            return {"status": "error", "error": "Process stdin not available"}
        
        try:
            session.process.stdin.close()
            return {"status": "ok", "message": "stdin closed"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def kill(self, session_id: str) -> dict:
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}
        
        if session.exited:
            return {"status": "already_exited", "exit_code": session.exit_code}
        
        try:
            session.process.terminate()
            try:
                session.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                session.process.kill()
                session.process.wait()
            
            session.exited = True
            session.exit_code = session.process.returncode
            self._move_to_finished(session)
            
            return {"status": "killed", "session_id": session.id}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def list_sessions(self) -> list:
        with self._lock:
            all_sessions = list(self._running.values()) + list(self._finished.values())
        
        result = []
        for s in all_sessions:
            entry = {
                "session_id": s.id,
                "command": s.command[:200],
                "cwd": s.cwd,
                "pid": s.pid,
                "uptime_seconds": int(time.time() - s.started_at),
                "status": "exited" if s.exited else "running",
                "output_preview": s.output_buffer[-200:] if s.output_buffer else "",
            }
            if s.exited:
                entry["exit_code"] = s.exit_code
            result.append(entry)
        
        return result


process_manager = ProcessManager()
