
import sqlite3
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL or SUPABASE_KEY not set")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def migrate_database():
    """Add brand_aliases column to analysis_sessions table"""
    
    print("🔄 Checking for 'brand_aliases' column in analysis_sessions table...")
    
    try:
        # We can't easily check columns via Supabase-py client directly like sqlite
        # But we can try to select the column and see if it fails, or just try to run the migration via SQLRPC if enabled
        # or just instruction the user.
        # However, supabase-py doesn't have a direct 'alter table' method unless we use the rpc call to a postgres function.
        # But wait, the user's project seems to be using Supabase mainly.
        # The previous migration.py (Step 19) used sqlite3 on 'brand_visibility.db'.
        # Database Manager (Step 32) says "Initialize Supabase database... Note: Tables should be created via Supabase SQL Editor".
        
        # It seems the project MIGHT be hybrid or transitioning. 
        # database_manager.py lines 17-23 initialize Supabase.
        # But migration.py (lines 10, 19) connects to 'brand_visibility.db' (SQLite).
        
        # Let's check which one is actually used in app.py.
        # app.py imports database_manager. 
        # database_manager.py uses Supabase exclusively (lines 41, 48, etc).
        
        # So migration.py might be old or for local fallback?
        # BUT database_manager.py ALSO has init_database() which prints SQL for Supabase.
        
        # Checking `database_manager.py` again.
        # Line 65: def init_database(): ... prints SQL instructions.
        
        # So I cannot run a migration script for Supabase from here easily unless I have SQL privileges via an RPC function or similar.
        # I should provide the SQL query to the user as requested.
        
        # However, if they are using SQLite locally as well (maybe for testing?), I should update that too if it exists.
        # The user has 'brand_visibility.db' in the file list (Step 6).
        
        if os.path.exists("brand_visibility.db"):
            print("Found local SQLite database. Updating...")
            conn = sqlite3.connect("brand_visibility.db")
            cursor = conn.cursor()
            
            # Check if column exists
            cursor.execute("PRAGMA table_info(analysis_sessions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'brand_aliases' in columns:
                print("✅ 'brand_aliases' column already exists in SQLite.")
            else:
                print("🔄 Adding 'brand_aliases' column to SQLite analysis_sessions table...")
                cursor.execute('ALTER TABLE analysis_sessions ADD COLUMN brand_aliases TEXT')
                conn.commit()
                print("✅ Migration successful for SQLite!")
            conn.close()
        else:
            print("⚠️ Local SQLite database not found.")

        print("\n" + "="*60)
        print("FOR SUPABASE (PRODUCTION):")
        print("Run the following SQL in your Supabase SQL Editor:")
        print("ALTER TABLE analysis_sessions ADD COLUMN brand_aliases JSONB;")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Migration error: {str(e)}")

if __name__ == "__main__":
    migrate_database()
