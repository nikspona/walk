# Walk Gallery

A Streamlit app to collect and display images, audio, text observations, and drawings with persistent storage using SQLite.

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

- **Text Input**: Add text observations and notes
- **Image Upload**: Upload and display images (PNG, JPG, JPEG)
- **Audio Recording**: Record and play audio using your device's microphone
- **Drawing Canvas**: Draw simple pictures or sketches of your walks
  - Works on both mobile (touch) and desktop (mouse)
  - Customizable brush size and colors
  - Touch-friendly interface for mobile devices
- **Gallery View**: Organized display of all content types in separate columns
- **Persistent Storage**: All content stored in SQLite database

## Drawing Feature

The drawing canvas is perfect for sketching:
- **Walk routes and paths**
- **Simple maps or directions**
- **Quick visual notes**
- **Artistic expressions**

**Mobile Support**: The drawing feature works seamlessly on phones and tablets with touch input, making it easy to sketch on the go.

## Usage

1. **Create Content**: Use the main page to add text, upload images, record audio, or create drawings
2. **Drawing**: Use the interactive canvas with customizable brush settings
3. **Submit**: Click "Add to Gallery" to save your content
4. **View Gallery**: Browse all your content organized by type
5. **Persistence**: All content is automatically saved and persists between sessions

## Requirements

- Python 3.7+
- Streamlit
- streamlit-drawable-canvas
- Pillow
- numpy

## Streamlit Cloud Compatibility

✅ **Fully compatible with Streamlit Cloud deployment**
- All dependencies are supported
- Drawing canvas works on mobile and desktop
- No additional system requirements needed 