#!/usr/bin/env python3
"""
HTML Gallery Generator for Walk Gallery
Generates a beautiful HTML page from PostgreSQL database contents
"""

import os
import json
import base64
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

def get_database_url():
    """Get PostgreSQL database URL from .env file or environment variables"""
    postgres_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    
    if not postgres_url:
        print("❌ DATABASE_URL environment variable is required!")
        print("💡 Create a .env file with: DATABASE_URL=postgresql://username:password@host:port/database")
        return None
    
    # Fix for some cloud providers that use postgres:// instead of postgresql://
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    return postgres_url

def get_posts_from_db():
    """Fetch all posts from PostgreSQL database"""
    database_url = get_database_url()
    if not database_url:
        return []
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Get all posts ordered by timestamp (newest first)
        cursor.execute("SELECT id, timestamp, datetime, content FROM posts ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
        posts = []
        for row in rows:
            try:
                post = {
                    'id': row[0],
                    'timestamp': row[1],
                    'datetime': row[2],
                    'content': json.loads(row[3])
                }
                posts.append(post)
            except json.JSONDecodeError as e:
                print(f"Skipping corrupted post: {e}")
                continue
        
        cursor.close()
        conn.close()
        return posts
        
    except Exception as e:
        print(f"Error retrieving posts: {e}")
        return []

def generate_html():
    """Generate beautiful minimalist HTML gallery from database content"""
    posts = get_posts_from_db()
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Walk Gallery</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --bg-primary: #fafafa;
            --bg-secondary: #ffffff;
            --text-primary: #1a1a1a;
            --text-secondary: #6b7280;
            --border: #e5e7eb;
            --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 300;
            margin-bottom: 3rem;
            text-align: center;
            letter-spacing: -0.025em;
        }}
        
        .gallery-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 4rem;
        }}
        
        .card {{
            background: var(--bg-secondary);
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            border: 1px solid var(--border);
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }}
        
        .card-image {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            background: var(--bg-primary);
        }}
        
        .card-content {{
            padding: 1.5rem;
        }}
        
        .text-content {{
            font-size: 1.125rem;
            line-height: 1.6;
            color: var(--text-primary);
            text-align: center;
            padding: 2rem 1rem;
            min-height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .audio-player {{
            padding: 1rem;
        }}
        
        .audio-controls {{
            width: 100%;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-secondary);
            grid-column: 1 / -1;
        }}
        
        .empty-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 1rem 0.5rem;
            }}
            
            h1 {{
                font-size: 2rem;
                margin-bottom: 2rem;
            }}
            
            .gallery-grid {{
                grid-template-columns: 1fr;
                gap: 1rem;
            }}
            
            .text-content {{
                font-size: 1rem;
                padding: 1.5rem 1rem;
                min-height: 100px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Walk Gallery</h1>

        <div class="gallery-grid">"""

    # Generate cards for each post in mixed order
    for post in posts:
        content = post['content']
        
        html_content += f"""
            <div class="card">"""
        
        # Handle different content types
        if 'text' in content:
            html_content += f"""
                <div class="text-content">
                    {content['text']}
                </div>"""
        
        elif 'image' in content:
            html_content += f"""
                <img class="card-image" src="data:{content['image']['type']};base64,{content['image']['data']}" alt="">"""
        
        elif 'drawing' in content:
            html_content += f"""
                <img class="card-image" src="data:{content['drawing']['type']};base64,{content['drawing']['data']}" alt="">"""
        
        elif 'audio' in content:
            html_content += f"""
                <div class="audio-player">
                    <audio class="audio-controls" controls>
                        <source src="data:{content['audio']['type']};base64,{content['audio']['data']}" type="{content['audio']['type']}">
                        Your browser does not support the audio element.
                    </audio>
                </div>"""
        
        html_content += """
            </div>"""

    # Empty state if no posts
    if not posts:
        html_content += """
            <div class="empty-state">
                <div class="empty-icon">📸</div>
                <h3>No content yet</h3>
                <p>Start creating your walk gallery</p>
            </div>"""

    html_content += f"""
        </div>
    </div>
</body>
</html>"""

    # Write to file
    with open('walk_gallery.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Minimalist gallery generated!")
    print(f"📊 {len(posts)} items mixed together")
    print(f"🌐 Open 'walk_gallery.html' in your browser")

if __name__ == "__main__":
    generate_html() 