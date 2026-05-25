from pathlib import Path
from typing import Dict


def read_file_capability(args: Dict, working_dir: Path) -> Dict:
    path = args.get('path', '')
    
    try:
        file_path = working_dir / path
        
        if not file_path.exists():
            return {"error": f"文件不存在: {path}"}
        
        if not file_path.is_file():
            return {"error": f"不是文件: {path}"}
        
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        return {
            "content": content,
            "lines": len(lines),
            "size": len(content),
            "success": True
        }
    except Exception as e:
        return {"error": str(e)}


def write_file_capability(args: Dict, working_dir: Path) -> Dict:
    path = args.get('path', '')
    content = args.get('content', '')
    
    try:
        file_path = working_dir / path
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content, encoding='utf-8')
        
        return {
            "path": str(file_path),
            "size": len(content),
            "success": True
        }
    except Exception as e:
        return {"error": str(e)}


def edit_file_capability(args: Dict, working_dir: Path) -> Dict:
    path = args.get('path', '')
    search = args.get('search', '')
    replace = args.get('replace', '')
    
    try:
        file_path = working_dir / path
        
        if not file_path.exists():
            return {"error": f"文件不存在: {path}"}
        
        content = file_path.read_text(encoding='utf-8')
        
        if search not in content:
            return {"error": f"未找到搜索内容"}
        
        new_content = content.replace(search, replace, 1)
        
        file_path.write_text(new_content, encoding='utf-8')
        
        return {
            "path": str(file_path),
            "success": True
        }
    except Exception as e:
        return {"error": str(e)}
