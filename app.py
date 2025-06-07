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
    system_prompt="You are a poet. You write poetry. You will be given a list of words and you will write a poem using those words. It should be a short abstract avant-garde concise poem, no need for rhyming.  The words are collected from a soundwalk that people in diffrent cities  around the world did together. Each persong collected words from their own walks. The poem should be a reflection of the common experience of the walk. Be creative but concise, avant-garde. Your style should be like early 20th century Ukrainian avant-garde poetry. The poem should be as short as possible, but still be a poem and use all the words provided. The poem should contain all the languages of the words provided. The words provided should be in markdown italics. ",
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

# Function to save a poem
def save_poem(words_list, poem_text):
    engine = get_db_engine()
    if engine is None:
        return False
    
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
        st.error(f"Error saving poem: {e}")
        return False

# Function to get the latest poem for given words
def get_latest_poem(words_list):
    engine = get_db_engine()
    if engine is None:
        return None
    
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
        st.error(f"Error retrieving poem: {e}")
        return None

# Initialize database on startup
init_db()

# Initialize session state for multi-step flow
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'post_data' not in st.session_state:
    st.session_state.post_data = {}
if 'show_gallery' not in st.session_state:
    st.session_state.show_gallery = False

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
                poem = poet.run_sync(words)
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
                        st.image(BytesIO(drawing_bytes))
                    
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
        
        # Drawing options
        col1, col2, col3 = st.columns(3)
        with col1:
            stroke_width = st.slider("Brush size", 1, 25, 3)
        with col2:
            stroke_color = st.color_picker("Brush color", "#000000")
        with col3:
            bg_color = st.color_picker("Background color", "#808080")
        
        # Create canvas
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_color=bg_color,
            background_image=None,
            update_streamlit=True,
            height=400,
            width=600,
            drawing_mode="freedraw",
            point_display_radius=0,
            display_toolbar=True,
            key="canvas",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Skip Drawing", use_container_width=True):
                next_step()
                st.rerun()
        
        with col2:
            if st.button("Next: Add Word →", use_container_width=True):
                # Save drawing if created
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
                
                next_step()
                st.rerun()
    
    # Step 2: Word
    elif st.session_state.current_step == 2:
        st.subheader("✍️ Type Your Word")
        st.write("Add a word or phrase that captures your walk.")
        
        text_input = st.text_input("Enter your word or phrase:", placeholder="Type something meaningful...")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Drawing", use_container_width=True):
                st.session_state.current_step = 1
                st.rerun()
        
        with col2:
            if st.button("Next: Add Picture →", use_container_width=True):
                # Save text if provided
                if text_input.strip():
                    st.session_state.post_data['text'] = text_input.strip()
                
                next_step()
                st.rerun()
    
    # Step 3: Picture
    elif st.session_state.current_step == 3:
        st.subheader("📸 Upload Your Picture")
        st.write("Share a photo from your walk or something that represents it.")
        
        uploaded_image = st.file_uploader("Choose an image file", type=["png", "jpg", "jpeg"])
        
        if uploaded_image:
            st.image(uploaded_image, caption="Your uploaded image", use_column_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Word", use_container_width=True):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            if st.button("Next: Add Sound →", use_container_width=True):
                # Save image if uploaded
                if uploaded_image:
                    bytes_data = uploaded_image.getvalue()
                    encoded = base64.b64encode(bytes_data).decode()
                    
                    st.session_state.post_data['image'] = {
                        'name': uploaded_image.name,
                        'type': uploaded_image.type,
                        'data': encoded
                    }
                
                next_step()
                st.rerun()
    
    # Step 4: Sound
    elif st.session_state.current_step == 4:
        st.subheader("🎵 Record Your Sound")
        st.write("Capture the sounds of your walk or record a voice note.")
        
        audio_input = st.audio_input("Record audio:")
        
        if audio_input:
            st.audio(audio_input)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Picture", use_container_width=True):
                st.session_state.current_step = 3
                st.rerun()
        
        with col2:
            if st.button("Finish & View Gallery →", use_container_width=True):
                # Save audio if recorded
                if audio_input:
                    bytes_data = audio_input.getvalue()
                    encoded = base64.b64encode(bytes_data).decode()
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.session_state.post_data['audio'] = {
                        'name': f"recording_{timestamp}.wav",
                        'type': "audio/wav",
                        'data': encoded
                    }
                
                # Create and save the final post
                if st.session_state.post_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    new_post = {
                        'id': str(uuid.uuid4()),
                        'timestamp': timestamp,
                        'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'content': st.session_state.post_data
                    }
                    
                    if save_post(new_post):
                        st.success("Your walk has been added to the gallery!")
                        go_to_gallery()
                        st.rerun()
                    else:
                        st.error("Failed to save your walk. Please try again.")
                else:
                    st.warning("Please add at least one type of content before finishing.")
    
    # Show existing gallery button if there are posts
    if get_posts():
        st.divider()
        if st.button("View Existing Gallery 🖼️", use_container_width=True):
            go_to_gallery()
            st.rerun() 