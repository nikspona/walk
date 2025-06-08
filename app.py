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
from pydantic_ai import Agent
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

poet = Agent(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    system_prompt="You are a poet. You write poetry. You will be given a word or a list of words and you will write a poem using ONLY those provided words. Do not use any other words except to connect the given words. It should be a short abstract avant-garde concise poem, no need for rhyming. The words are collected from a soundwalk that people in diffrent cities around the world did together. Each persong collected words from their own walks. The poem should be a reflection of the common experience of the walk. Your style should be like early 20th century Ukrainian avant-garde poetry. The poem should contain all the languages of the words provided by the user. ",
)

# Set page config
st.set_page_config(page_title="Soundwalk", page_icon="📸", layout="wide")

# Database configuration
def get_database_url():
    """Get PostgreSQL database URL from environment"""
    postgres_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    
    if not postgres_url:
        st.error("❌ DATABASE_URL environment variable is required!")
        st.stop()
    
    # Fix for some cloud providers that use postgres:// instead of postgresql://
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    return postgres_url

@st.cache_resource
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
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return engine
        
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        st.stop()

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
            
            # Create poems table
            create_poems_table_sql = """
            CREATE TABLE IF NOT EXISTS poems (
                id TEXT PRIMARY KEY,
                words TEXT NOT NULL,
                poem TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            conn.execute(text(create_poems_table_sql))
            
            # Create index for better performance
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_timestamp ON posts(timestamp)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_poems_created_at ON poems(created_at)"))
            except:
                # Index might already exist
                pass
            
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        st.stop()

# Function to save a post
def save_post(post):
    engine = get_db_engine()
    if engine is None:
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
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
            if attempt < max_retries - 1:
                # Clear the cached engine and try again
                get_db_engine.clear()
                continue
            else:
                # Only show error on final attempt
                return False
    
    return False

# Function to get all posts
@st.cache_data(ttl=60, show_spinner=False)  # Cache for 60 seconds, hide spinner
def get_posts():
    engine = get_db_engine()
    if engine is None:
        return []
    
    max_retries = 3
    for attempt in range(max_retries):
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
                        # Skip corrupted post silently
                        continue
                
                return posts
                
        except Exception as e:
            if attempt < max_retries - 1:
                # Clear the cached engine and try again
                get_db_engine.clear()
                continue
            else:
                # Return empty list silently on final attempt
                return []
    
    return []

# Function to save a poem
def save_poem(words_list, poem_text):
    engine = get_db_engine()
    if engine is None:
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                # Create a unique ID for the poem
                poem_id = str(uuid.uuid4())
                words_string = " • ".join(words_list)
                
                # Insert into database
                conn.execute(
                    text("INSERT INTO poems (id, words, poem) VALUES (:id, :words, :poem)"),
                    {
                        'id': poem_id,
                        'words': words_string,
                        'poem': poem_text
                    }
                )
                conn.commit()
                return True
                
        except Exception as e:
            if attempt < max_retries - 1:
                # Clear the cached engine and try again
                get_db_engine.clear()
                continue
            else:
                # Return False on final attempt
                return False
    
    return False

# Function to get the latest poem for given words
def get_latest_poem(words_list):
    engine = get_db_engine()
    if engine is None:
        return None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                words_string = " • ".join(words_list)
                
                # Get the most recent poem for these exact words
                result = conn.execute(
                    text("SELECT poem FROM poems WHERE words = :words ORDER BY created_at DESC LIMIT 1"),
                    {'words': words_string}
                )
                row = result.fetchone()
                
                if row:
                    return row[0]
                return None
                
        except Exception as e:
            if attempt < max_retries - 1:
                # Clear the cached engine and try again
                get_db_engine.clear()
                continue
            else:
                # Return None on final attempt (will generate new poem)
                return None
    
    return None

# Function to clear all poems (admin function)
def clear_all_poems():
    """Clear all poems from the database"""
    engine = get_db_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM poems"))
            conn.commit()
            return True
            
    except Exception as e:
        st.error(f"Error clearing poems: {e}")
        return False

# Initialize database on startup
init_db()

# Initialize session state for multi-step flow
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'post_data' not in st.session_state:
    st.session_state.post_data = {}
if 'show_gallery' not in st.session_state:
    st.session_state.show_gallery = False
if 'pending_post' not in st.session_state:
    st.session_state.pending_post = None

def reset_creation_flow():
    """Reset the creation flow to start over"""
    st.session_state.current_step = 1
    st.session_state.post_data = {}
    st.session_state.show_gallery = False

def next_step():
    """Move to the next step in the creation flow"""
    st.session_state.current_step += 1

def go_to_gallery():
    """Navigate to gallery"""
    st.session_state.show_gallery = True

def go_to_create():
    """Navigate to create flow"""
    st.session_state.show_gallery = False
    reset_creation_flow()

# Application title

# Main content
if st.session_state.show_gallery:
    # Gallery Page
    
    # Handle background saving of pending post
    if 'pending_post' in st.session_state and st.session_state.pending_post:
        pending_post = st.session_state.pending_post
        
        # Try to save in background
        if save_post(pending_post):
            # Clear the pending post and refresh cache
            st.session_state.pending_post = None
            get_posts.clear()
        else:
            st.error("❌ Failed to save your walk. Please try again.")
            # Keep the pending post for retry
    
    # Get posts from database
    posts = get_posts()
    
    # Display posts with words grouped together
    if posts:
        # Separate words from other content
        words = []
        other_content = []
        
        for post in posts:
            content = post['content']
            if 'text' in content:
                words.append(content['text'])
            
            # Check if post has non-text content
            has_other_content = any(key in content for key in ['image', 'drawing', 'audio'])
            if has_other_content:
                other_content.append(post)
        
        # Display words section
        if words:
            # Display words in a flowing text format
            words_text = " • ".join(words)
            st.markdown(f"**{words_text}**")
            
            # Check if we already have a poem for these words
            existing_poem = get_latest_poem(words)
            
            if existing_poem:
                # Display existing poem
                st.markdown(existing_poem)
            else:
                # Generate new poem and save it
                poem = poet.run_sync(f"User words: {words}")
                poem_text = poem.output
                
                # Save the poem to database
                save_poem(words, poem_text)
                
                # Display the poem
                st.markdown(poem_text)
            
            st.divider()
        
        # Display other content in grid
        if other_content:
            # Create responsive columns for media content
            cols = st.columns([1, 1, 1, 1])
            
            for i, post in enumerate(other_content):
                with cols[i % 4]:
                    content = post['content']
                    
                    # Display image content
                    if 'image' in content:
                        image_bytes = base64.b64decode(content['image']['data'])
                        st.image(BytesIO(image_bytes))
                    
                    # Display drawing content
                    if 'drawing' in content:
                        drawing_bytes = base64.b64decode(content['drawing']['data'])
                        st.image(BytesIO(drawing_bytes), width=300)
                    
                    # Display audio content
                    if 'audio' in content:
                        audio_bytes = base64.b64decode(content['audio']['data'])
                        st.audio(audio_bytes, format=content['audio']['type'])
    else:
        st.info("No content yet. Add some content from the create page!")
    
    # Create new content button at the bottom
    st.divider()
    if st.button("+ Create New Content", use_container_width=True):
        go_to_create()
        st.rerun()

else:
    # Multi-step Content Creation Flow
    
    # Step 1: Drawing
    if st.session_state.current_step == 1:
        st.subheader("🎨 Draw Your Walk")
        st.write("Create a drawing that represents your walk or experience.")
        
        # Create canvas
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#808080",
            background_image=None,
            update_streamlit=True,
            height=400,
            width=600,
            drawing_mode="freedraw",
            point_display_radius=0,
            display_toolbar=True,
            key="canvas",
        )
        
        # Save drawing immediately when created
        has_drawing = False
        if canvas_result.image_data is not None and np.any(canvas_result.image_data[:,:,3] > 0):
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            img_rgb = Image.new('RGB', img.size, (255, 255, 255))
            img_rgb.paste(img, mask=img.split()[3])
            
            img_buffer = BytesIO()
            img_rgb.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            encoded = base64.b64encode(img_bytes).decode()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.post_data['drawing'] = {
                'name': f"drawing_{timestamp}.png",
                'type': "image/png",
                'data': encoded
            }
            has_drawing = True
        
        col1, col2 = st.columns(2)
        with col1:
            # Only enable next button if there's a drawing
            if has_drawing or 'drawing' in st.session_state.post_data:
                if st.button("Next: Add Word →", use_container_width=True):
                    next_step()
                    st.rerun()
            else:
                st.button("Next: Add Word →", use_container_width=True, disabled=True)
                st.caption("Create a drawing to continue")
        
        with col2:
            pass  # Empty column for spacing
    
    # Step 2: Word
    elif st.session_state.current_step == 2:
        st.subheader("✍️ Type Your Word")
        st.write("Add a word or phrase that captures your walk.")
        
        # Get existing text if any
        existing_text = st.session_state.post_data.get('text', '')
        text_input = st.text_input("Enter your word or phrase:", value=existing_text, placeholder="Type something meaningful...")
        
        # Save text immediately when entered
        if text_input.strip():
            st.session_state.post_data['text'] = text_input.strip()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Drawing", use_container_width=True):
                st.session_state.current_step = 1
                st.rerun()
        
        with col2:
            # Only enable next button if there's text
            if text_input.strip():
                if st.button("Next: Add Picture →", use_container_width=True):
                    next_step()
                    st.rerun()
            else:
                st.button("Next: Add Picture →", use_container_width=True, disabled=True)
                st.caption("Enter a word or phrase to continue")
    
    # Step 3: Picture
    elif st.session_state.current_step == 3:
        st.subheader("📸 Upload Your Picture")
        st.write("Share a photo from your walk or something that represents it.")
        
        uploaded_image = st.file_uploader("Choose an image file", type=["png", "jpg", "jpeg"], label_visibility="hidden")
        
        has_image = False
        if uploaded_image:
            st.image(uploaded_image, use_container_width=True)
            
            # Save image immediately when uploaded
            bytes_data = uploaded_image.getvalue()
            encoded = base64.b64encode(bytes_data).decode()
            
            st.session_state.post_data['image'] = {
                'name': uploaded_image.name,
                'type': uploaded_image.type,
                'data': encoded
            }
            has_image = True
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Word", use_container_width=True):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            # Only enable next button if there's an image
            if has_image or 'image' in st.session_state.post_data:
                if st.button("Next: Add Sound →", use_container_width=True):
                    next_step()
                    st.rerun()
            else:
                st.button("Next: Add Sound →", use_container_width=True, disabled=True)
                st.caption("Upload an image to continue")
    
    # Step 4: Sound
    elif st.session_state.current_step == 4:
        st.subheader("🎵 Record Your Sound")
        st.write("Capture the sounds of your walk or record a voice note.")
        
        audio_input = st.audio_input("Record audio:")
        
        has_audio = False
        if audio_input:
            st.audio(audio_input)
            
            # Save audio immediately when recorded
            bytes_data = audio_input.getvalue()
            encoded = base64.b64encode(bytes_data).decode()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.post_data['audio'] = {
                'name': f"recording_{timestamp}.wav",
                'type': "audio/wav",
                'data': encoded
            }
            has_audio = True
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Picture", use_container_width=True):
                st.session_state.current_step = 3
                st.rerun()
        
        with col2:
            # Only enable finish button if there's audio
            if has_audio or 'audio' in st.session_state.post_data:
                if st.button("Finish & View Gallery →", use_container_width=True):
                    # Check if user has any content
                    if st.session_state.post_data:
                        # Store the post data for background saving
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        st.session_state.pending_post = {
                            'id': str(uuid.uuid4()),
                            'timestamp': timestamp,
                            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'content': st.session_state.post_data.copy()
                        }
                        
                        # Clear cache and show gallery immediately
                        get_posts.clear()
                        st.success("Your walk is being added to the gallery, please wait!")
                        go_to_gallery()
                        st.rerun()
                    else:
                        st.warning("Please add at least one type of content before finishing.")
            else:
                st.button("Finish & View Gallery →", use_container_width=True, disabled=True)
                st.caption("Record audio to finish")
    
    # Show existing gallery button if there are posts
    if get_posts():
        st.divider()
        if st.button("View Existing Gallery 🖼️", use_container_width=True):
            go_to_gallery()
            st.rerun() 