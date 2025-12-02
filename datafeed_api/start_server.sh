#!/bin/bash

echo "🚀 Starting Fight Judge AI Data Feed API..."
echo "=========================================="
echo ""

cd /app/datafeed_api

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with Supabase credentials"
    exit 1
fi

# Check if database is set up
echo "Checking database connection..."
python3 -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_db():
    try:
        # Try to connect with alternative URL format
        url = 'postgresql://postgres.yymuzbgipozkaxqabtxb:Cletalily349!@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require'
        conn = await asyncpg.connect(url, timeout=10)
        
        # Check if tables exist
        tables = await conn.fetchval(\"\"\"
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'events'
        \"\"\")
        
        await conn.close()
        
        if tables > 0:
            print('✅ Database connection successful')
            print('✅ Tables exist')
            exit(0)
        else:
            print('⚠️  Database connected but tables not found')
            print('Please run the migration SQL in Supabase SQL Editor')
            exit(1)
    except Exception as e:
        print(f'⚠️  Database connection issue: {e}')
        print('The API will start but may fail until database is set up')
        exit(2)

asyncio.run(check_db())
" 

DB_STATUS=$?

if [ $DB_STATUS -eq 0 ]; then
    echo ""
    echo "✅ Database is ready!"
elif [ $DB_STATUS -eq 1 ]; then
    echo ""
    echo "⚠️  Please run the SQL migration first!"
    echo "See: /app/datafeed_api/SETUP_INSTRUCTIONS.md"
    echo ""
    echo "Continuing anyway (server will start but endpoints may fail)..."
elif [ $DB_STATUS -eq 2 ]; then
    echo ""
    echo "⚠️  Cannot verify database status"
    echo "Continuing anyway..."
fi

echo ""
echo "=========================================="
echo "Starting API server on port 8002..."
echo "=========================================="
echo ""

# Start the server
python3 main.py
