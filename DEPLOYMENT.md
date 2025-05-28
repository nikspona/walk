# Deploying Walk Gallery to Streamlit Cloud

## Prerequisites

1. A GitHub account
2. Your code pushed to a GitHub repository

## Deployment Steps

1. **Create a GitHub repository**

   If you haven't already:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/walk-gallery.git
   git push -u origin main
   ```

2. **Sign up for Streamlit Cloud**

   - Go to [Streamlit Cloud](https://streamlit.io/cloud)
   - Sign in with your GitHub account

3. **Deploy your app**

   - Click "New app"
   - Select your repository
   - Set the main file path to "app.py"
   - Click "Deploy"

4. **Access your app**

   Once deployed, Streamlit Cloud will provide a URL where your app is hosted.

## Important Notes About Persistent Storage

The app uses SQLite for persistent storage. In Streamlit Cloud:

1. **Database Location**: The database file is stored in the `data/` directory. This is part of the app's ephemeral storage.

2. **Data Persistence**: While SQLite provides persistence within a single deployment, be aware that:
   - If your app is redeployed, the database will be reset
   - If Streamlit Cloud needs to move your app to a different server, data might be lost

3. **For true persistence**: Consider upgrading to a more robust solution like:
   - PostgreSQL on a managed service
   - MongoDB Atlas
   - Firebase
   - Supabase

## Scaling Considerations

For a production app with many users:

1. **Upgrade from SQLite**: When user load increases, consider migrating to a proper database service
2. **Media Storage**: For large media files, consider using a dedicated service like AWS S3, Google Cloud Storage, or similar
3. **Authentication**: Add user authentication if needed for user-specific content 