import streamlit as st
import os
import base64
import json
import uuid
from datetime import datetime
from io import BytesIO
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image
import psycopg2
from sqlalchemy import create_engine, text

# Set page config
st.set_page_config(page_title="Walk Gallery", page_icon="📸", layout="wide")

# Database configuration
def get_database_url():
    """Get PostgreSQL database URL from environment"""
    postgres_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    
    if not postgres_url:
        st.error("❌ DATABASE_URL environment variable is required!")
        st.info("Please set DATABASE_URL to your PostgreSQL connection string")
        st.stop()
    
    # Fix for some cloud providers that use postgres:// instead of postgresql://
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    return postgres_url

def get_db_engine():
    """Get SQLAlchemy engine for PostgreSQL"""
    try:
        database_url = get_database_url()
        
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "sslmode": "require",
                "connect_timeout": 10
            }
        )
        
        return engine
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize PostgreSQL database tables"""
    engine = get_db_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            # Create table for PostgreSQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                datetime TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            conn.execute(text(create_table_sql))
            
            # Create index for better performance
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_timestamp ON posts(timestamp)"))
            except:
                # Index might already exist
                pass
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        return False


# Function to save a post
def save_post(post):
    engine = get_db_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            # Convert content dict to JSON string
            content_json = json.dumps(post['content'])
            
            # Insert into database
            conn.execute(
                text("INSERT INTO posts (id, timestamp, datetime, content) VALUES (:id, :timestamp, :datetime, :content)"),
                {
                    'id': post['id'],
                    'timestamp': post['timestamp'],
                    'datetime': post['datetime'],
                    'content': content_json
                }
            )
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Error saving post: {e}")
        return False

# Function to get all posts
def get_posts():
    engine = get_db_engine()
    if engine is None:
        return []
    
    try:
        with engine.connect() as conn:
            # Get all posts ordered by timestamp (newest first)
            result = conn.execute(text("SELECT id, timestamp, datetime, content FROM posts ORDER BY timestamp DESC"))
            rows = result.fetchall()
            
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
                    st.warning(f"Skipping corrupted post: {e}")
                    continue
            
            return posts
            
    except Exception as e:
        st.error(f"Error retrieving posts: {e}")
        return []

# Function to delete a post
def delete_post(post_id):
    engine = get_db_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("DELETE FROM posts WHERE id = :id"), {'id': post_id})
            conn.commit()
            return result.rowcount > 0
            
    except Exception as e:
        st.error(f"Error deleting post: {e}")
        return False

# Function to get database statistics
def get_db_stats():
    engine = get_db_engine()
    if engine is None:
        return {}
    
    try:
        with engine.connect() as conn:
            # Get total number of posts
            result = conn.execute(text("SELECT COUNT(*) FROM posts"))
            total_posts = result.fetchone()[0]
            
            # Get posts by content type
            result = conn.execute(text("SELECT content FROM posts"))
            rows = result.fetchall()
            
            stats = {
                'total_posts': total_posts,
                'text_posts': 0,
                'image_posts': 0,
                'drawing_posts': 0,
                'audio_posts': 0,
                'database_type': 'PostgreSQL'
            }
            
            for row in rows:
                try:
                    content = json.loads(row[0])
                    if 'text' in content:
                        stats['text_posts'] += 1
                    if 'image' in content:
                        stats['image_posts'] += 1
                    if 'drawing' in content:
                        stats['drawing_posts'] += 1
                    if 'audio' in content:
                        stats['audio_posts'] += 1
                except json.JSONDecodeError:
                    continue
            
            return stats
            
    except Exception as e:
        st.error(f"Error getting database stats: {e}")
        return {}

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
            if save_post(new_post):
                st.success("Content saved to database successfully!")
                # Automatically navigate to gallery after submission
                navigate_to_gallery()
                st.rerun()
            else:
                st.error("Failed to save content to database. Please try again.")
        else:
            st.warning("Please add some content before submitting.")
else:
    # Gallery Page
    st.header("Gallery")
    
    # Back button and database stats
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("← Create New Content", type="primary"):
            navigate_to_create()
            st.rerun()
    
    with col2:
        # Show database statistics
        stats = get_db_stats()
        if stats:
            st.metric("Total Posts", stats.get('total_posts', 0))
    
    # Show detailed stats in an expander
    with st.expander("📊 Database Statistics"):
        if stats:
            # Show database type prominently
            st.info(f"Database: {stats.get('database_type', 'Unknown')}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Text Posts", stats.get('text_posts', 0))
            with col2:
                st.metric("Audio Posts", stats.get('audio_posts', 0))
            with col3:
                st.metric("Images", stats.get('image_posts', 0))
            with col4:
                st.metric("Drawings", stats.get('drawing_posts', 0))
        else:
            st.info("Unable to load database statistics")
    
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
                    with st.container():
                        st.markdown(f"**{post['content']['text'].upper()}**")
                        st.caption(f"Created: {post['datetime']}")
            else:
                st.info("No text content yet.")
        
        # Sounds column
        with col2:
            st.subheader("Sounds")
            audio_posts = [post for post in posts if 'audio' in post['content']]
            if audio_posts:
                for post in audio_posts:
                    with st.container():
                        audio_bytes = base64.b64decode(post['content']['audio']['data'])
                        st.audio(audio_bytes, format=post['content']['audio']['type'])
                        st.caption(f"Created: {post['datetime']}")
            else:
                st.info("No audio recordings yet.")
        
        # Images column
        with col3:
            st.subheader("Images")
            image_posts = [post for post in posts if 'image' in post['content']]
            if image_posts:
                for post in image_posts:
                    with st.container():
                        image_bytes = base64.b64decode(post['content']['image']['data'])
                        st.image(BytesIO(image_bytes))
                        st.caption(f"Created: {post['datetime']}")
            else:
                st.info("No images uploaded yet.")
        
        # Drawings column
        with col4:
            st.subheader("Drawings")
            drawing_posts = [post for post in posts if 'drawing' in post['content']]
            if drawing_posts:
                for post in drawing_posts:
                    with st.container():
                        drawing_bytes = base64.b64decode(post['content']['drawing']['data'])
                        st.image(BytesIO(drawing_bytes), caption="Walk Drawing")
                        st.caption(f"Created: {post['datetime']}")
            else:
                st.info("No drawings yet.")
    else:
        st.info("No content yet. Add some content from the create page!") 