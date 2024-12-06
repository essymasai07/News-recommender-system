import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'user_interactions.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    # Create interactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interactions (
        user_id INTEGER,
        article_title TEXT,
        article_link TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()

def add_user(username, hashed_password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()

def get_user(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()  # Returns None if no user is found
    conn.close()
    return user

def log_user_interaction(user_id, article_title, article_link):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO interactions (user_id, article_title, article_link) 
    VALUES (?, ?, ?)
    ''', (user_id, article_title, article_link))

    conn.commit()
    conn.close()

def get_user_interactions(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT article_title, article_link FROM interactions 
    WHERE user_id = ? 
    ORDER BY timestamp DESC
    ''', (user_id,))
    
    interactions = cursor.fetchall()
    conn.close()
    return interactions

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM users WHERE id = ?
    ''', (user_id,))
    
    user = cursor.fetchone()  # Returns None if no user is found
    conn.close()
    return user
