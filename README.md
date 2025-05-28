# Walk Gallery

A Streamlit app to collect and display images, audio, and text observations with persistent storage using SQLite.

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the app:
   ```
   streamlit run app.py
   ```

## Deployment

This app can be deployed using Streamlit Cloud (https://streamlit.io/cloud):

1. Push this repository to GitHub
2. Sign in to Streamlit Cloud with your GitHub account
3. Click "New app" and select this repository
4. Select app.py as the main file
5. Click "Deploy"

## Features

- Add text observations
- Upload and display images (PNG, JPG, JPEG)
- Upload and play audio files (MP3, WAV, OGG)
- Chronological display of all observations
- Persistent storage using SQLite database

## Usage

- Use the sidebar to add new content (text, images, or audio)
- Click "Add to Gallery" to save your content
- All content is stored in a SQLite database for persistence
- Content is automatically displayed in chronological order

## Requirements

- Python 3.7+
- Streamlit
- sqlite-utils 