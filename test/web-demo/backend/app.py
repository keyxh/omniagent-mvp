"""
智能笔记系统 - Flask 后端
端口: 5001
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# ── 应用初始化 ─────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'notes.db')

# ── 数据库初始化 ───────────────────────────────────────
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典格式
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '无标题',
            content TEXT NOT NULL DEFAULT '',
            color TEXT DEFAULT 'default',
            pinned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("[OK] 数据库初始化成功")

# ── 基础路由 ───────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': '智能笔记系统 API 服务运行中',
        'version': '1.0.0',
        'endpoints': [
            'GET    /api/notes       - 获取所有笔记',
            'POST   /api/notes       - 创建新笔记',
            'PUT    /api/notes/<id>  - 更新笔记',
            'DELETE /api/notes/<id>  - 删除笔记',
            'GET    /api/search?q=   - 搜索笔记'
        ]
    })

@app.route('/api/notes', methods=['GET'])
def get_notes():
    """获取所有笔记"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM notes ORDER BY pinned DESC, updated_at DESC')
        results = cursor.fetchall()
        
        notes_data = []
        for row in results:
            notes_data.append({
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'color': row['color'],
                'pinned': row['pinned'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        return jsonify({'success': True, 'notes': notes_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/notes', methods=['POST'])
def create_note():
    """创建新笔记"""
    conn = None
    try:
        title = request.json.get('title', '无标题')
        content = request.json.get('content', '')
        color = request.json.get('color', 'default')
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO notes (title, content, color) VALUES (?, ?, ?)',
            (title, content, color)
        )
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': '笔记创建成功',
            'note': {
                'id': cursor.lastrowid,
                'title': title,
                'content': content,
                'color': color,
                'pinned': 0,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/notes/<int:id>', methods=['PUT'])
def update_note(id):
    """更新笔记"""
    conn = None
    try:
        data = request.json
        conn = get_db()
        cursor = conn.cursor()
        
        if 'title' in data:
            cursor.execute('UPDATE notes SET title=? WHERE id=?', (data['title'], id))
        if 'content' in data:
            cursor.execute('UPDATE notes SET content=? WHERE id=?', (data['content'], id))
        if 'color' in data:
            cursor.execute('UPDATE notes SET color=? WHERE id=?', (data['color'], id))
        
        conn.commit()
        
        cursor.execute('SELECT * FROM notes WHERE id=?', (id,))
        row = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'message': '笔记更新成功',
            'note': {
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'color': row['color'],
                'pinned': row['pinned'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/notes/<int:id>', methods=['DELETE'])
def delete_note(id):
    """删除笔记"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM notes WHERE id=?', (id,))
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'笔记 {id} 删除成功'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/search', methods=['GET'])
def search_notes():
    """搜索笔记"""
    conn = None
    try:
        query = request.args.get('q', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        if query:
            cursor.execute(
                'SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC',
                ('%' + query + '%', '%' + query + '%')
            )
        else:
            cursor.execute('SELECT * FROM notes ORDER BY pinned DESC, updated_at DESC')
        
        results = cursor.fetchall()
        notes_data = []
        for row in results:
            notes_data.append({
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'color': row['color'],
                'pinned': row['pinned'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        return jsonify({'success': True, 'notes': notes_data, 'query': query})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ── 启动入口 ───────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("[OK] 智能笔记系统后端启动: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
