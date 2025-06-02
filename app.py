import streamlit as st
import os
import base64
import json
import sqlite3
import uuid
from datetime import datetime
from io import BytesIO
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image

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

# Function to check if running on Streamlit Cloud
def is_streamlit_cloud():
    return os.environ.get('STREAMLIT_SHARING_MODE') == 'streamlit_cloud'

# Alert for Streamlit Cloud users
if is_streamlit_cloud():
    st.warning("""
    ⚠️ This app is running on Streamlit Cloud using a temporary database. 
    Any data you add will be lost when the app restarts.
    For persistent storage, deploy with a cloud database solution.
    """)

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
    
    # Text input - using regular text_input instead of text_area for better Safari compatibility
    st.subheader("Type Your Word")
    text_input = st.text_input("Type Your Word", key="text_input", label_visibility="hidden")
    
    # Image upload
    st.subheader("Upload Your Image")
    uploaded_image = st.file_uploader("Upload Your Image", type=["png", "jpg", "jpeg"], label_visibility="hidden")
    
    # Drawing canvas
    st.subheader("Draw Your Walk")
    
    # Drawing options
    col1, col2, col3 = st.columns(3)
    with col1:
        stroke_width = st.slider("Brush size", 1, 25, 3)
    with col2:
        stroke_color = st.color_picker("Brush color", "#000000")
    with col3:
        bg_color = st.color_picker("Background color", "#FFFFFF")
    
    # Create canvas
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some transparency
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color=bg_color,
        background_image=None,
        update_streamlit=True,
        height=300,
        width=400,
        drawing_mode="freedraw",
        point_display_radius=0,
        display_toolbar=True,
        key="canvas",
    )
    
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
        if text_input or uploaded_image or audio_input or (canvas_result.image_data is not None and np.any(canvas_result.image_data[:,:,3] > 0)):
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
            
            # Add drawing if created
            if canvas_result.image_data is not None and np.any(canvas_result.image_data[:,:,3] > 0):
                # Convert canvas to PIL Image
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                
                # Convert to RGB (remove alpha channel) and save as PNG
                img_rgb = Image.new('RGB', img.size, (255, 255, 255))
                img_rgb.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                
                # Convert to bytes
                img_buffer = BytesIO()
                img_rgb.save(img_buffer, format='PNG')
                img_bytes = img_buffer.getvalue()
                
                # Encode to base64
                encoded = base64.b64encode(img_bytes).decode()
                
                new_post['content']['drawing'] = {
                    'name': f"drawing_{timestamp}.png",
                    'type': "image/png",
                    'data': encoded
                }
                st.success("Drawing added successfully!")
            
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
    
    # Display posts grouped by type in columns
    if posts:
        # Create four columns for different content types
        col1, col2, col3, col4 = st.columns(4)
        
        # Words column
        with col1:
            st.subheader("Words")
            text_posts = [post for post in posts if 'text' in post['content']]
            if text_posts:
                for post in text_posts:
                    st.markdown(f"**{post['content']['text'].upper()}**")
            else:
                st.info("No text content yet.")
        
        # Sounds column
        with col2:
            st.subheader("Sounds")
            audio_posts = [post for post in posts if 'audio' in post['content']]
            if audio_posts:
                for post in audio_posts:
                    audio_bytes = base64.b64decode(post['content']['audio']['data'])
                    st.audio(audio_bytes, format=post['content']['audio']['type'])
            else:
                st.info("No audio recordings yet.")
        
        # Images column
        with col3:
            st.subheader("Images")
            image_posts = [post for post in posts if 'image' in post['content']]
            if image_posts:
                for post in image_posts:
                    image_bytes = base64.b64decode(post['content']['image']['data'])
                    st.image(BytesIO(image_bytes))
            else:
                st.info("No images uploaded yet.")
        
        # Drawings column
        with col4:
            st.subheader("Drawings")
            drawing_posts = [post for post in posts if 'drawing' in post['content']]
            if drawing_posts:
                for post in drawing_posts:
                    drawing_bytes = base64.b64decode(post['content']['drawing']['data'])
                    st.image(BytesIO(drawing_bytes), caption="Walk Drawing")
            else:
                st.info("No drawings yet.")
    else:
        st.info("No content yet. Add some content from the create page!") 