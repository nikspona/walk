import streamlit as st
import os
import base64
import json
import sqlite3
import uuid
from datetime import datetime
from io import BytesIO

# Set page config
st.set_page_config(page_title="Walk Gallery", page_icon="📸", layout="wide")

# Function to initialize database
def init_db():
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
    c = conn.cursor()
    
    # Convert content dict to JSON string, then to binary
    content_json = json.dumps(post['content'])
    
    # Insert into database
    c.execute(
        "INSERT INTO posts (id, timestamp, datetime, content) VALUES (?, ?, ?, ?)",
        (post['id'], post['timestamp'], post['datetime'], content_json)
    )
    
    conn.commit()
    conn.close()

# Function to get all posts
def get_posts():
    conn = init_db()
    c = conn.cursor()
    
    # Get all posts ordered by timestamp (newest first)
    c.execute("SELECT id, timestamp, datetime, content FROM posts ORDER BY timestamp DESC")
    rows = c.fetchall()
    
    posts = []
    for row in rows:
        post = {
            'id': row[0],
            'timestamp': row[1],
            'datetime': row[2],
            'content': json.loads(row[3])  # Convert JSON string back to dict
        }
        posts.append(post)
    
    conn.close()
    return posts

# Initialize database on startup
init_db()

# Create navigation
show_gallery = st.session_state.get("show_gallery", False)

def navigate_to_gallery():
    st.session_state.show_gallery = True

def navigate_to_create():
    st.session_state.show_gallery = False

# Application title
st.title("Walk Gallery")

# Main content
if not show_gallery:
    # Content Creation Page
    
    # Text input
    st.subheader("Type Your Word")
    text_input = st.text_area("Type Your Word", height=150, label_visibility="hidden")
    
    # Image upload
    st.subheader("Upload Your Image")
    uploaded_image = st.file_uploader("Upload Your Image", type=["png", "jpg", "jpeg"], label_visibility="hidden")
    
    # Audio recording with native st.audio_input
    st.subheader("Record Your Sound")
    audio_input = st.audio_input("Record Your Sound", label_visibility="hidden")
    
    # Buttons - now stacked vertically
    # Submit button
    submit = st.button("Add to Gallery", type="primary", use_container_width=True)
    
    # View gallery button (only shown if there are posts)
    if get_posts():
        view_gallery = st.button("View Gallery 🖼️", use_container_width=True)
        if view_gallery:
            navigate_to_gallery()
            st.rerun()
    
    if submit:
        if text_input or uploaded_image or audio_input:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create a new post with all media types
            new_post = {
                'id': str(uuid.uuid4()),
                'timestamp': timestamp,
                'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'content': {}
            }
            
            # Add text if provided
            if text_input:
                new_post['content']['text'] = text_input
                st.success("Text added successfully!")
            
            # Add image if uploaded
            if uploaded_image:
                # Convert file to base64 for storage
                bytes_data = uploaded_image.getvalue()
                encoded = base64.b64encode(bytes_data).decode()
                
                new_post['content']['image'] = {
                    'name': uploaded_image.name,
                    'type': uploaded_image.type,
                    'data': encoded
                }
                st.success("Image uploaded successfully!")
            
            # Add audio if recorded
            if audio_input:
                # Convert file to base64 for storage
                bytes_data = audio_input.getvalue()
                encoded = base64.b64encode(bytes_data).decode()
                
                new_post['content']['audio'] = {
                    'name': f"recording_{timestamp}.wav",
                    'type': "audio/wav",
                    'data': encoded
                }
                st.success("Audio recorded successfully!")
            
            # Save the post to database
            save_post(new_post)
            
            # Automatically navigate to gallery after submission
            navigate_to_gallery()
            st.rerun()
        else:
            st.warning("Please add some content before submitting.")
else:
    # Gallery Page
    st.header("Gallery")
    
    # Back button
    if st.button("← Create New Content", type="primary"):
        navigate_to_create()
        st.rerun()
    
    # Get posts from database
    posts = get_posts()
    
    # Display posts
    if posts:
        for i, post in enumerate(posts):
            with st.container():
                                
                # Display text content
                if 'text' in post['content']:
                    st.markdown(f"**{post['content']['text'].upper()}**")
                
                # Display audio content first
                if 'audio' in post['content']:
                    # Decode base64 data
                    audio_bytes = base64.b64decode(post['content']['audio']['data'])
                    st.audio(audio_bytes, format=post['content']['audio']['type'])
                
                # Display image content after audio
                if 'image' in post['content']:
                    # Decode base64 data
                    image_bytes = base64.b64decode(post['content']['image']['data'])
                    st.image(BytesIO(image_bytes))
                
                st.divider()  # Add a divider between posts
    else:
        st.info("No content yet. Add some content from the create page!") 