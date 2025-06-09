# Cloudinary Setup Guide

This guide will help you set up Cloudinary for media storage in your Soundwalk app.

## 🚀 Why Cloudinary?

- **Scalability**: Handles thousands of concurrent uploads
- **Performance**: Global CDN for fast media delivery
- **Free Tier**: 25GB storage, 25GB bandwidth/month
- **Automatic Optimization**: Images are automatically optimized for web

## 📋 Setup Steps

### 1. Create Cloudinary Account

1. Go to [cloudinary.com](https://cloudinary.com)
2. Sign up for a free account
3. Verify your email address

### 2. Get Your Credentials

1. Go to your Cloudinary Dashboard
2. Copy these three values:
   - **Cloud Name** (e.g., `dxyz123abc`)
   - **API Key** (e.g., `123456789012345`)
   - **API Secret** (e.g., `abcdefghijklmnopqrstuvwxyz123456`)

### 3. Configure Streamlit Cloud

#### Option A: Using Streamlit Secrets (Recommended)

In your Streamlit Cloud app settings, add to secrets:

```toml
# .streamlit/secrets.toml
CLOUDINARY_CLOUD_NAME = "your_cloud_name_here"
CLOUDINARY_API_KEY = "your_api_key_here"
CLOUDINARY_API_SECRET = "your_api_secret_here"
```

#### Option B: Environment Variables

Set these environment variables in your Streamlit Cloud app:

```
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
```

### 4. Local Development Setup

Create a `.env` file in your project root:

```env
# .env
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
```

## 🔧 Features Enabled

With Cloudinary integration, your app now:

✅ **Reduces memory usage** by 90%+ (no more base64 storage)  
✅ **Handles concurrent uploads** from 30+ users  
✅ **Automatically optimizes** images for web  
✅ **Provides global CDN** for fast loading  
✅ **Maintains backward compatibility** with existing data  

## 📊 File Organization

Your media files will be organized in Cloudinary as:

```
soundwalk/
├── images/          # User uploaded photos
├── drawings/        # Canvas drawings
└── audio/           # Voice recordings
```

## 🔒 Security Features

- **Secure uploads** via HTTPS
- **Automatic file validation**
- **Malware scanning** (on paid plans)
- **Access control** options available

## 💰 Pricing

**Free Tier Limits:**
- 25GB storage
- 25GB bandwidth/month
- 1,000 transformations/month

**Paid Plans start at $99/month** for higher limits.

For 30 concurrent users, the free tier should be sufficient initially.

## 🚨 Troubleshooting

### Common Issues:

1. **"Failed to upload" errors**
   - Check your API credentials
   - Verify internet connection
   - Check Cloudinary dashboard for quota limits

2. **Images not displaying**
   - Verify the URL is accessible
   - Check browser console for errors
   - Ensure Cloudinary account is active

3. **Slow uploads**
   - This is normal for large files
   - Consider image compression settings
   - Check your internet connection

### Testing Your Setup

You can test your Cloudinary setup locally:

```python
import cloudinary
import cloudinary.uploader

# Configure
cloudinary.config(
    cloud_name="your_cloud_name",
    api_key="your_api_key", 
    api_secret="your_api_secret"
)

# Test upload
try:
    result = cloudinary.uploader.upload("test_image.jpg")
    print(f"✅ Upload successful: {result['secure_url']}")
except Exception as e:
    print(f"❌ Upload failed: {e}")
```

## 📈 Performance Benefits

**Before Cloudinary:**
- 30 users × 5MB average content = 150MB in database
- Slow page loads due to base64 decoding
- Memory issues with concurrent users

**After Cloudinary:**
- 30 users × ~1KB URL storage = 30KB in database
- Fast loading via CDN
- No memory issues with media files

## 🔄 Migration Notes

- **Existing data**: Old base64 data will still work (backward compatibility)
- **New uploads**: Will automatically use Cloudinary
- **No data loss**: Your existing content remains accessible

## 📞 Support

If you encounter issues:

1. Check Cloudinary dashboard for error logs
2. Verify your account quota usage
3. Test with smaller files first
4. Contact Cloudinary support if needed 