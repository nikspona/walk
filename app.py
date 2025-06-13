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
import time
from functools import lru_cache
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Load environment variables from .env file (for local development)
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

poet = Agent(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    system_prompt="You are a poet. You write poetry. You will be given a word or a list of words and you will write a poem using those provided words. Use as few other words to connect the given words as possible. It should be a short abstract avant-garde concise poem, no need for rhyming. The words are collected from a soundwalk that people in diffrent cities around the world did together. Each persong collected words from their own walks. The poem should be a reflection of the common experience of the walk. Your style should be like early 20th century Ukrainian avant-garde poetry. The poem should contain all the languages of the words provided by the user, you can use several languages in one poem. ",
)

# Set page config
st.set_page_config(page_title="Soundwalk", page_icon="📸", layout="wide")

# Add after the imports
WHATSAPP_GROUP_LINK = "https://chat.whatsapp.com/G2gS8w712Ty0kFhXJn3F07"  # Another Walk WhatsApp group

def show_whatsapp_fallback():
    """Show WhatsApp fallback message only for critical errors that affect media saving"""
    st.error("⚠️ We're having trouble with the app. Please try again in a few minutes or join our WhatsApp group and share your walk with the community.")
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background-color: #1a1a1a; border-radius: 10px; margin: 20px 0; border: 1px solid #333;'>
        <h3 style='color: #ffffff; margin-bottom: 15px;'>Join our WhatsApp Group</h3>
        <p style='color: #cccccc; margin-bottom: 20px;'>Get updates and share your walk with the community</p>
        <a href='{WHATSAPP_GROUP_LINK}' target='_blank' style='display: inline-block; background-color: #25D366; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin-top: 10px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
            Join WhatsApp Group
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Database configuration
def get_database_url():
    """Get PostgreSQL database URL from environment"""
    postgres_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    
    if not postgres_url:
        show_whatsapp_fallback()  # Make database URL missing a critical error
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
            pool_size=5,
            max_overflow=5,
            pool_timeout=30,
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
        show_whatsapp_fallback()  # Show WhatsApp fallback for any database connection error
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
        show_whatsapp_fallback()
        return False

# Function to save a post
def save_post(post):
    engine = get_db_engine()
    if engine is None:
        show_whatsapp_fallback()
        return False
    
    # Track failed attempts in session state
    if 'save_attempts' not in st.session_state:
        st.session_state.save_attempts = 0
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                content_json = json.dumps(post['content'])
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
                # Reset save attempts on success
                st.session_state.save_attempts = 0
                return True
                
        except Exception as e:
            if attempt < max_retries - 1:
                get_db_engine.clear()
                continue
            else:
                # Increment failed attempts
                st.session_state.save_attempts += 1
                
                # Show WhatsApp fallback after multiple save failures
                if st.session_state.save_attempts >= 2:
                    show_whatsapp_fallback()
                else:
                    st.error("❌ Failed to save your walk. Please try again.")
                return False
    
    return False

# Function to get all posts
@st.cache_data(ttl=30, show_spinner=False)
def get_posts():
    engine = get_db_engine()
    if engine is None:
        show_whatsapp_fallback()  # Show WhatsApp fallback if no database connection
    
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
                        continue
                
                return posts
                
        except Exception as e:
            if attempt < max_retries - 1:
                get_db_engine.clear()
                continue
            else:
                show_whatsapp_fallback()  # Show WhatsApp fallback after all retries fail
    
    show_whatsapp_fallback()  # Show WhatsApp fallback if we get here
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
        show_whatsapp_fallback()
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

# Add rate limiting for poem generation
last_poem_generation = {}
POEM_GENERATION_COOLDOWN = 10  # seconds between poem generations per user

# Media upload functions
def upload_image_to_cloudinary(image_bytes, filename):
    """Upload image to Cloudinary and return URL"""
    try:
        result = cloudinary.uploader.upload(
            image_bytes,
            public_id=f"soundwalk/images/{filename}_{uuid.uuid4()}",
            resource_type="image",
            quality="auto:best",
            fetch_format="auto",
            eager=[
                {"quality": "auto:best", "fetch_format": "auto"}
            ]
        )
        return result.get('secure_url')
    except Exception as e:
        show_whatsapp_fallback()  # Show WhatsApp fallback for any upload error
        return None

def upload_audio_to_cloudinary(audio_bytes, filename):
    """Upload audio to Cloudinary and return URL"""
    try:
        result = cloudinary.uploader.upload(
            audio_bytes,
            public_id=f"soundwalk/audio/{filename}_{uuid.uuid4()}",
            resource_type="video"
        )
        return result.get('secure_url')
    except Exception as e:
        show_whatsapp_fallback()  # Show WhatsApp fallback for any upload error
        return None

def upload_drawing_to_cloudinary(image_bytes, filename):
    """Upload drawing to Cloudinary and return URL"""
    try:
        result = cloudinary.uploader.upload(
            image_bytes,
            public_id=f"soundwalk/drawings/{filename}_{uuid.uuid4()}",
            resource_type="image",
            format="png",
            quality="auto:best",
            transformation=[
                {"width": 800, "height": 800, "crop": "limit"},
                {"quality": "auto:best"}
            ]
        )
        return result.get('secure_url')
    except Exception as e:
        show_whatsapp_fallback()  # Show WhatsApp fallback for any upload error
        return None

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

# Initialize user ID for rate limiting
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

def can_generate_poem():
    """Check if user can generate a poem (rate limiting)"""
    user_id = st.session_state.get('user_id', 'anonymous')
    current_time = time.time()
    
    if user_id in last_poem_generation:
        time_since_last = current_time - last_poem_generation[user_id]
        if time_since_last < POEM_GENERATION_COOLDOWN:
            return False, POEM_GENERATION_COOLDOWN - time_since_last
    
    last_poem_generation[user_id] = current_time
    return True, 0

def generate_poem_with_rate_limit(words):
    """Generate poem with rate limiting"""
    can_generate, wait_time = can_generate_poem()
    
    if not can_generate:
        return None  # Silent failure - don't show warning to user
    
    try:
        poem = poet.run_sync(f"User words: {words}")
        return poem.output
    except Exception as e:
        return None  # Silent failure - don't show error to user

# Application title

# Main content
if st.session_state.show_gallery:
    # Gallery Page
    
    # Handle background saving of pending post
    if 'pending_post' in st.session_state and st.session_state.pending_post:
        pending_post = st.session_state.pending_post
        
        # Try to save in background
        if save_post(pending_post):
            st.session_state.pending_post = None
            st.cache_data.clear()
        else:
            # Error message is now handled in save_post based on attempt count
            pass  # Remove the generic error message since it's handled in save_post
    
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
                poem_text = generate_poem_with_rate_limit(words)
                
                if poem_text:
                    # Save the poem to database
                    save_poem(words, poem_text)
                    
                    # Display the poem
                    st.markdown(poem_text)
                # If poem generation fails, nothing is shown
            
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
                        if 'url' in content['image']:
                            # New format with Cloudinary URL
                            st.image(content['image']['url'])
                        else:
                            # Legacy format with base64 data (for backward compatibility)
                            image_bytes = base64.b64decode(content['image']['data'])
                            st.image(BytesIO(image_bytes))
                    
                    # Display drawing content
                    if 'drawing' in content:
                        if 'url' in content['drawing']:
                            # New format with Cloudinary URL
                            st.image(content['drawing']['url'], width=300)
                        else:
                            # Legacy format with base64 data (for backward compatibility)
                            drawing_bytes = base64.b64decode(content['drawing']['data'])
                            st.image(BytesIO(drawing_bytes), width=300)
                    
                    # Display audio content
                    if 'audio' in content:
                        if 'url' in content['audio']:
                            # New format with Cloudinary URL
                            st.audio(content['audio']['url'])
                        else:
                            # Legacy format with base64 data (for backward compatibility)
                            audio_bytes = base64.b64decode(content['audio']['data'])
                            st.audio(audio_bytes, format=content['audio']['type'])
    else:
        # Show create button without the info message
        pass
    
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
            background_color="#FFFFFF",
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
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"drawing_{timestamp}"
            
            # Upload to Cloudinary
            with st.spinner("Uploading drawing..."):
                drawing_url = upload_drawing_to_cloudinary(img_bytes, filename)
                
            if drawing_url:
                st.session_state.post_data['drawing'] = {
                    'name': f"{filename}.png",
                    'type': "image/png",
                    'url': drawing_url
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
            
            # Check if we already have this image uploaded (compare filename)
            current_filename = uploaded_image.name.split('.')[0]
            existing_image = st.session_state.post_data.get('image', {})
            
            if 'url' not in existing_image or current_filename not in existing_image.get('name', ''):
                # Upload to Cloudinary only if it's a new image
                bytes_data = uploaded_image.getvalue()
                
                with st.spinner("Uploading image..."):
                    image_url = upload_image_to_cloudinary(bytes_data, current_filename)
                    
                if image_url:
                    st.session_state.post_data['image'] = {
                        'name': uploaded_image.name,
                        'type': uploaded_image.type,
                        'url': image_url
                    }
            
            # Image exists (either just uploaded or from previous upload)
            if 'image' in st.session_state.post_data:
                has_image = True
            # If upload fails, user can try uploading again
        
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
            
            # Check if we already have audio uploaded (check if audio exists in session)
            if 'audio' not in st.session_state.post_data:
                # Upload to Cloudinary only once
                bytes_data = audio_input.getvalue()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}"
                
                with st.spinner("Uploading audio..."):
                    audio_url = upload_audio_to_cloudinary(bytes_data, filename)
                    
                if audio_url:
                    st.session_state.post_data['audio'] = {
                        'name': f"{filename}.wav",
                        'type': "audio/wav",
                        'url': audio_url
                    }
            
            # Audio exists (either just uploaded or from previous upload)
            if 'audio' in st.session_state.post_data:
                has_audio = True
            # If upload fails, user can try recording again
        
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
                        
                        # Show gallery immediately
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