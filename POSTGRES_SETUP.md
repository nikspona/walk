# PostgreSQL Setup Guide for Walk Gallery

This guide will help you set up PostgreSQL for your Walk Gallery app on Streamlit Cloud.

## 🚀 Quick Setup Options

### Option 1: Supabase (Recommended - Free Tier Available)

1. **Create Supabase Account**
   - Go to [supabase.com](https://supabase.com)
   - Sign up with GitHub
   - Create a new project

_7>CPxmH5EuvJ*s


2. **Get Database URL**
   - Go to Settings → Database
   - Copy the "Connection string" under "Connection parameters"
   - It looks like: `postgresql://postgres:[password]@[host]:5432/postgres`

   postgresql://postgres.jhvgjodssqgmuhgxwybn:_7>CPxmH5EuvJ*s
@aws-0-eu-central-2.pooler.supabase.com:6543/postgres

3. **Add to Streamlit Cloud**
   - In your Streamlit Cloud app settings
   - Go to "Secrets" section
   - Add: `DATABASE_URL = "your_connection_string_here"`

### Option 2: Neon (Serverless PostgreSQL)

1. **Create Neon Account**
   - Go to [neon.tech](https://neon.tech)
   - Sign up and create a database
   - Copy the connection string

2. **Add to Streamlit Cloud**
   - Add `DATABASE_URL` in Streamlit secrets

### Option 3: Railway

1. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Create a PostgreSQL database
   - Copy the connection URL

### Option 4: Heroku Postgres

1. **Create Heroku App**
   - Add Heroku Postgres addon
   - Get `DATABASE_URL` from config vars

## 🔧 Streamlit Cloud Configuration

### Method 1: Environment Variables (Recommended)

In your Streamlit Cloud app settings:

```toml
# .streamlit/secrets.toml
DATABASE_URL = "postgresql://username:password@host:port/database"
```

### Method 2: Direct Environment Variable

Set `DATABASE_URL` in the app's environment variables section.

## 🗄️ Database Schema

The app will automatically create this table:

```sql
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    datetime TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON posts(timestamp);
```

## 📊 Connection String Format

Your `DATABASE_URL` should look like:

```
postgresql://username:password@hostname:port/database_name
```

Example:
```
postgresql://myuser:mypassword@db.example.com:5432/mydatabase
```

## 🔒 Security Best Practices

1. **Never commit database URLs to Git**
2. **Use environment variables or Streamlit secrets**
3. **Enable SSL (most providers do this by default)**
4. **Use strong passwords**
5. **Limit database user permissions if possible**

## 🚨 Troubleshooting

### Common Issues

1. **"DATABASE_URL environment variable is required!"**
   - Make sure you've set the `DATABASE_URL` in Streamlit secrets
   - Check the connection string format

2. **SSL Connection Errors**
   - Most cloud providers require SSL
   - The app automatically sets `sslmode=require`

3. **Connection Timeouts**
   - Check if your database allows external connections
   - Verify the hostname and port

4. **Authentication Errors**
   - Double-check username and password
   - Ensure the database user has CREATE and INSERT permissions

### Testing Your Connection

You can test your connection string locally:

```python
import psycopg2
from sqlalchemy import create_engine

# Test connection
try:
    engine = create_engine("your_database_url_here")
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## 📈 Performance Tips

1. **Connection Pooling**: The app uses SQLAlchemy's connection pooling
2. **Indexes**: Automatic index on timestamp for faster queries
3. **Connection Recycling**: Connections are recycled every 5 minutes

## 💰 Cost Considerations

- **Supabase**: 500MB free, then $25/month
- **Neon**: 3GB free, then $19/month  
- **Railway**: $5/month for PostgreSQL
- **Heroku**: $5/month for basic PostgreSQL

## 🔄 Migration from SQLite

If you have existing SQLite data, you'll need to:

1. Export data from SQLite
2. Import into PostgreSQL
3. Update connection string

The table schema is compatible between both databases.

## 📞 Support

If you encounter issues:

1. Check Streamlit Cloud logs
2. Verify your connection string
3. Test connection locally first
4. Check your database provider's documentation 