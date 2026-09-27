import sqlite3

def init_db():
    conn = sqlite3.connect('archlink.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            role TEXT,
            phone TEXT,
            skills TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_id INTEGER,
            title TEXT,
            description TEXT,
            budget TEXT,
            status TEXT DEFAULT 'OPEN'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bids (
            bid_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            architect_id INTEGER,
            proposal_price TEXT,
            delivery_days TEXT
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()