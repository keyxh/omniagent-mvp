import re
from pathlib import Path
from typing import Dict, List


def grep_capability(args: Dict, working_dir: Path) -> Dict:
    pattern = args.get('pattern', '')
    search_path = args.get('path', '.')
    
    try:
        base_path = working_dir / search_path
        
        if not base_path.exists():
            return {"error": f"路径不存在: {search_path}"}
        
        matches = []
        
        if base_path.is_file():
            files = [base_path]
        else:
            files = list(base_path.rglob('*'))
            files = [f for f in files if f.is_file()]
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        matches.append({
                            "file": str(file_path.relative_to(working_dir)),
                            "line": line_num,
                            "content": line.strip()
                        })
            except:
                continue
        
        return {
            "matches": matches,
            "count": len(matches),
            "success": True
        }
    except Exception as e:
        return {"error": str(e)}


def glob_capability(args: Dict, working_dir: Path) -> Dict:
    pattern = args.get('pattern', '')
    
    try:
        files = list(working_dir.glob(pattern))
        files.extend(working_dir.rglob(pattern))
        
        files = list(set(files))
        files = [f for f in files if f.is_file()]
        
        file_list = [str(f.relative_to(working_dir)) for f in files]
        
        return {
            "files": file_list,
            "count": len(file_list),
            "success": True
        }
    except Exception as e:
        return {"error": str(e)}
