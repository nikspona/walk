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

## Custom Domain Setup (anotherwal.com)

### Option 1: Streamlit Cloud + Cloudflare (Recommended)

1. **Deploy to Streamlit Cloud first** (follow steps above)
2. **Purchase domain**: Buy `anotherwal.com` from any registrar
3. **Set up Cloudflare**:
   - Create free Cloudflare account
   - Add your domain to Cloudflare
   - Update nameservers to Cloudflare's
4. **Configure DNS**:
   - Create CNAME record: `@` → `your-app.streamlit.app`
   - Enable proxy (orange cloud icon)
5. **SSL**: Cloudflare provides free SSL automatically

### Option 2: Deploy to DigitalOcean/Railway/Render

For full domain control, deploy to a cloud platform:

**DigitalOcean App Platform**:
```bash
# Create Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Railway**:
- Connect GitHub repo
- Add custom domain in Railway dashboard
- Point DNS A record to Railway's IP

**Render**:
- Connect GitHub repo  
- Add custom domain in Render dashboard
- Configure DNS as instructed

### Option 3: VPS Deployment

Deploy on your own server (DigitalOcean Droplet, AWS EC2, etc.):

1. **Set up server**:
```bash
# Install dependencies
sudo apt update
sudo apt install python3 python3-pip nginx certbot python3-certbot-nginx

# Clone your repo
git clone https://github.com/yourusername/walk-gallery.git
cd walk-gallery
pip3 install -r requirements.txt
```

2. **Configure Nginx**:
```nginx
# /etc/nginx/sites-available/anotherwal.com
server {
    listen 80;
    server_name anotherwal.com www.anotherwal.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

3. **Enable site and SSL**:
```bash
sudo ln -s /etc/nginx/sites-available/anotherwal.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d anotherwal.com -d www.anotherwal.com
```

4. **Run app**:
```bash
streamlit run app.py --server.port=8501
```

## Features Supported on Streamlit Cloud

✅ **All features work perfectly on Streamlit Cloud:**
- Text input and display
- Image upload and viewing
- Audio recording and playback
- **Drawing canvas with touch support** (works on mobile and desktop)
- SQLite database storage
- Gallery organization

## Drawing Feature Compatibility

The `streamlit-drawable-canvas` component is fully supported on Streamlit Cloud:
- **Mobile devices**: Touch drawing works seamlessly
- **Desktop**: Mouse/trackpad drawing functions perfectly
- **No additional configuration needed**

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
2. **Media Storage**: For large media files and drawings, consider using a dedicated service like AWS S3, Google Cloud Storage, or similar
3. **Authentication**: Add user authentication if needed for user-specific content 