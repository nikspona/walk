import streamlit as st
import os
import json
import sqlite3
import psycopg2
from psycopg2.extras import Json

# Check if running on Streamlit Cloud
def is_streamlit_cloud():
    return os.environ.get('STREAMLIT_SHARING_MODE') == 'streamlit_cloud' or os.environ.get('IS_PROD', '') == 'true'

# Initialize database connection based on environment
def init_db():
    if is_streamlit_cloud():
        # Use PostgreSQL in production (Streamlit Cloud)
        # Get credentials from Streamlit secrets
        try:
            conn = psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                database=st.secrets["postgres"]["database"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"],
                port=st.secrets["postgres"]["port"]
            )
            
            # Create posts table if not exists
            with conn.cursor() as c:
                c.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    datetime TEXT,
                    content JSONB
                )
                ''')
                conn.commit()
                
            return conn
        except Exception as e:
            st.error(f"Failed to connect to PostgreSQL: {e}")
            # Fall back to SQLite if PostgreSQL connection fails
            return init_sqlite_db()
    else:
        # Use SQLite for local development
        return init_sqlite_db()

def init_sqlite_db():
    # Create data directory if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # Connect to SQLite database (will create if not exists)
    conn = sqlite3.connect('data/gallery.db')
    c = conn.cursor()
    
    # Create table if it doesn't exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        datetime TEXT,
        content BLOB
    )
    ''')
    
    conn.commit()
    return conn

# Function to save a post
def save_post(post):
    conn = init_db()
    
    # Convert content dict to JSON string
    content_json = json.dumps(post['content'])
    
    if isinstance(conn, sqlite3.Connection):
        # SQLite connection
        c = conn.cursor()
        c.execute(
            "INSERT INTO posts (id, timestamp, datetime, content) VALUES (?, ?, ?, ?)",
            (post['id'], post['timestamp'], post['datetime'], content_json)
        )
    else:
        # PostgreSQL connection
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO posts (id, timestamp, datetime, content) VALUES (%s, %s, %s, %s)",
                (post['id'], post['timestamp'], post['datetime'], content_json)
            )
    
    conn.commit()
    conn.close()

# Function to get all posts
def get_posts():
    conn = init_db()
    posts = []
    
    if isinstance(conn, sqlite3.Connection):
        # SQLite connection
        c = conn.cursor()
        c.execute("SELECT id, timestamp, datetime, content FROM posts ORDER BY timestamp DESC")
        rows = c.fetchall()
        
        for row in rows:
            post = {
                'id': row[0],
                'timestamp': row[1],
                'datetime': row[2],
                'content': json.loads(row[3])  # Convert JSON string back to dict
            }
            posts.append(post)
    else:
        # PostgreSQL connection
        with conn.cursor() as c:
            c.execute("SELECT id, timestamp, datetime, content FROM posts ORDER BY timestamp DESC")
            rows = c.fetchall()
            
            for row in rows:
                post = {
                    'id': row[0],
                    'timestamp': row[1],
                    'datetime': row[2],
                    'content': row[3] if isinstance(row[3], dict) else json.loads(row[3])
                }
                posts.append(post)
    
    conn.close()
    return posts 