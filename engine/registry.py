import threading
from dataclasses import dataclass, field
from typing import Dict, Callable, Optional, List, Any
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    name: str
    handler: Callable
    description: str
    parameters: Dict
    check_fn: Optional[Callable] = None
    check_cache_ttl: float = 300.0
    category: str = "general"
    requires: List[str] = field(default_factory=list)
    _last_check: float = 0.0
    _last_result: bool = True


class ToolRegistry:
    
    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._lock = threading.RLock()
        self._generation = 0
        self._cli_instances: Dict[str, Any] = {}
    
    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Dict,
        check_fn: Optional[Callable] = None,
        category: str = "general",
        requires: Optional[List[str]] = None
    ):
        with self._lock:
            entry = ToolEntry(
                name=name,
                handler=handler,
                description=description,
                parameters=parameters,
                check_fn=check_fn,
                category=category,
                requires=requires or []
            )
            self._tools[name] = entry
            self._generation += 1
            logger.info(f"Registered tool: {name} (category: {category})")
    
    def is_available(self, name: str) -> bool:
        with self._lock:
            if name not in self._tools:
                return False
            
            entry = self._tools[name]
            
            if entry.check_fn is None:
                return True
            
            now = time.time()
            if now - entry._last_check < entry.check_cache_ttl:
                return entry._last_result
            
            try:
                result = entry.check_fn()
                entry._last_result = result
                entry._last_check = now
                return result
            except Exception as e:
                logger.warning(f"Check failed for tool {name}: {e}")
                entry._last_result = False
                entry._last_check = now
                return False
    
    def get_tool(self, name: str) -> Optional[ToolEntry]:
        with self._lock:
            return self._tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        with self._lock:
            if category:
                return [
                    name for name, entry in self._tools.items()
                    if entry.category == category
                ]
            return list(self._tools.keys())
    
    def get_openai_functions(self) -> List[Dict]:
        with self._lock:
            functions = []
            for name, entry in self._tools.items():
                if self.is_available(name):
                    functions.append({
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": entry.description,
                            "parameters": entry.parameters
                        }
                    })
            return functions
    
    def register_cli(self, cli_instance):
        cli_name = cli_instance.name
        with self._lock:
            self._cli_instances[cli_name] = cli_instance
            
            for tool_name, tool_info in cli_instance.tools.items():
                full_name = f"{cli_name}_{tool_name}"
                self.register(
                    name=full_name,
                    handler=tool_info.handler,
                    description=tool_info.description,
                    parameters=tool_info.parameters,
                    category=tool_info.category,
                    requires=tool_info.requires
                )
            
            logger.info(f"Registered CLI: {cli_name} with {len(cli_instance.tools)} tools")
    
    def get_cli(self, cli_name: str):
        with self._lock:
            return self._cli_instances.get(cli_name)
    
    def list_clis(self) -> List[str]:
        with self._lock:
            return list(self._cli_instances.keys())


_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    return _registry


def _register_builtin_tools():
    from .shell import shell_capability
    from .filesystem import read_file_capability, write_file_capability, edit_file_capability
    from .search import grep_capability, glob_capability
    
    registry = get_registry()
    
    registry.register(
        name="shell",
        handler=shell_capability,
        description="Execute a shell command and return the output",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                }
            },
            "required": ["command"]
        },
        category="system"
    )
    
    registry.register(
        name="read_file",
        handler=read_file_capability,
        description="Read contents of a file",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["path"]
        },
        category="filesystem"
    )
    
    registry.register(
        name="write_file",
        handler=write_file_capability,
        description="Write content to a file",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        },
        category="filesystem"
    )
    
    registry.register(
        name="edit_file",
        handler=edit_file_capability,
        description="Edit a file using SEARCH/REPLACE pattern",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "search": {
                    "type": "string",
                    "description": "Text to search for"
                },
                "replace": {
                    "type": "string",
                    "description": "Text to replace with"
                }
            },
            "required": ["path", "search", "replace"]
        },
        category="filesystem"
    )
    
    registry.register(
        name="grep",
        handler=grep_capability,
        description="Search for pattern in files",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Path to search in (file or directory)"
                }
            },
            "required": ["pattern"]
        },
        category="search"
    )
    
    registry.register(
        name="glob",
        handler=glob_capability,
        description="Find files matching a pattern",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '*.py', '**/*.txt')"
                }
            },
            "required": ["pattern"]
        },
        category="search"
    )


_register_builtin_tools()


def get_capabilities() -> List[Dict]:
    return get_registry().get_openai_functions()


def execute_capability(name: str, args: Dict, working_dir) -> Any:
    registry = get_registry()
    tool = registry.get_tool(name)
    
    if tool is None:
        raise ValueError(f"Unknown capability: {name}")
    
    if not registry.is_available(name):
        raise RuntimeError(f"Capability not available: {name}")
    
    return tool.handler(args, working_dir)
