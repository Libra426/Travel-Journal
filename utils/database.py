"""SQLite 数据访问层：用户与手账的私有化存储。

数据表：
- users：登录账号（用户名唯一，密码使用 Werkzeug 哈希存储）
- journals：手账数据（以 JSON 形式保存，按 user_id 隔离实现私有化）
"""
import os
import json
import sqlite3
from fractions import Fraction

from werkzeug.security import generate_password_hash

# 数据库文件放在项目根目录
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS journals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_journals_user_id ON journals (user_id);
    ''')
    conn.commit()
    conn.close()


# ===== 用户 =====
def create_user(username, password_hash):
    conn = get_conn()
    cur = conn.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (username, password_hash)
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def has_any_user():
    conn = get_conn()
    row = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()
    conn.close()
    return row['c'] > 0


# ===== 手账 =====
def list_journals(user_id):
    conn = get_conn()
    rows = conn.execute(
        'SELECT data FROM journals WHERE user_id = ? ORDER BY id ASC', (user_id,)
    ).fetchall()
    conn.close()
    return [json.loads(r['data']) for r in rows]


def get_journal(user_id, journal_id):
    conn = get_conn()
    row = conn.execute(
        'SELECT data FROM journals WHERE user_id = ? AND id = ?',
        (user_id, journal_id)
    ).fetchone()
    conn.close()
    return json.loads(row['data']) if row else None


def _json_default(o):
    """json.dumps 兜底：把 bytes / Fraction(IFDRational) 等非 JSON 类型转为可序列化值，
    避免单条脏数据把整次上传打成 500。"""
    if isinstance(o, bytes):
        return o.decode('utf-8', errors='replace')
    if isinstance(o, Fraction):
        return float(o)
    return str(o)


def create_journal(user_id, journal_data):
    conn = get_conn()
    nid = conn.execute('SELECT COALESCE(MAX(id), 0) + 1 FROM journals').fetchone()[0]
    journal_data['id'] = str(nid)
    conn.execute(
        'INSERT INTO journals (id, user_id, data) VALUES (?, ?, ?)',
        (nid, user_id, json.dumps(journal_data, ensure_ascii=False, default=_json_default))
    )
    conn.commit()
    conn.close()
    return journal_data


def update_journal_row(user_id, journal_id, journal_data):
    conn = get_conn()
    cur = conn.execute(
        'UPDATE journals SET data = ? WHERE user_id = ? AND id = ?',
        (json.dumps(journal_data, ensure_ascii=False), user_id, journal_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def delete_journal_row(user_id, journal_id):
    conn = get_conn()
    cur = conn.execute(
        'DELETE FROM journals WHERE user_id = ? AND id = ?',
        (user_id, journal_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def import_legacy_journals(journals_file):
    """首次启动时，把旧的 journals.json 迁移到默认账号（admin / 123456）。

    仅当用户表为空且旧文件存在时执行一次，避免重复导入。
    """
    if has_any_user():
        return
    if not os.path.exists(journals_file):
        return
    try:
        with open(journals_file, 'r', encoding='utf-8') as f:
            journals = json.load(f)
    except (json.JSONDecodeError, OSError):
        return
    if not journals:
        return

    user_id = create_user('admin', generate_password_hash('123456'))
    for j in journals:
        if isinstance(j, dict):
            create_journal(user_id, dict(j))
    print('[时光手账] 已创建默认账号 admin / 123456，并导入旧手账数据。')
