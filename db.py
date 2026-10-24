import sqlite3
import os
from datetime import datetime

DB_NAME = "warehouse.db"

def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        shift TEXT DEFAULT '',
        pallet TEXT DEFAULT '',
        updated_at TEXT DEFAULT (datetime('now'))
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT NOT NULL,
        pallet TEXT NOT NULL,
        shift TEXT,
        user_id INTEGER,
        username TEXT,
        full_name TEXT,
        added_at TEXT DEFAULT (datetime('now'))
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scans_barcode ON scans(barcode)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scans_pallet ON scans(pallet)")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, username, full_name) VALUES (?,?,?)", (user_id, '', ''))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
    res = dict(row)
    conn.close()
    return res

def update_user(user_id, **kwargs):
    if not kwargs: return
    sets = ','.join([f"{k}=?" for k in kwargs])
    vals = list(kwargs.values()) + [user_id]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {sets}, updated_at=datetime('now') WHERE user_id=?", vals)
    conn.commit()
    conn.close()

def add_scan(barcode, pallet, shift, user_id, username='', full_name=''):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO scans (barcode, pallet, shift, user_id, username, full_name) VALUES (?,?,?,?,?,?)",
                (barcode, pallet, shift, user_id, username, full_name))
    conn.commit()
    conn.close()

def find_by_barcode(barcode):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM scans WHERE barcode=? ORDER BY added_at DESC", (barcode,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_pallets():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pallet, COUNT(*) as count, MAX(added_at) as last_added FROM scans GROUP BY pallet ORDER BY last_added DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_pallet_items(pallet):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM scans WHERE pallet=? ORDER BY added_at DESC", (pallet,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
