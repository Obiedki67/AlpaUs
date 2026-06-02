import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS testers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            tg_username TEXT,
            nickname TEXT,
            friend_code TEXT UNIQUE,
            device_name TEXT UNIQUE,
            license_key TEXT UNIQUE,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_all_tester_tg_ids():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT tg_id FROM testers")
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result

def get_tester_count_by_android_version():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT android_version, COUNT(*) FROM testers GROUP BY android_version")
    result = c.fetchall()
    conn.close()
    return result

def user_exists_by_tg(tg_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM testers WHERE tg_id=?", (tg_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def friend_code_exists(friend_code):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM testers WHERE friend_code=?", (friend_code,))
    result = c.fetchone()
    conn.close()
    return result is not None

def device_exists(device_name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM testers WHERE device_name=?", (device_name,))
    result = c.fetchone()
    conn.close()
    return result is not None

def register_tester(tg_id, tg_username, nickname, friend_code, device_name, license_key):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO testers (tg_id, tg_username, nickname, friend_code, device_name, license_key)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (tg_id, tg_username, nickname, friend_code, device_name, license_key))
    conn.commit()
    conn.close()

def get_all_testers():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT nickname, friend_code, device_name, license_key, registered_at FROM testers")
    result = c.fetchall()
    conn.close()
    return result

def get_tester_count():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM testers")
    count = c.fetchone()[0]
    conn.close()
    return count
