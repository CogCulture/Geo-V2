"""
Database Migration: Add 'industry' column to analysis_sessions table

Run this script once to update your existing database.
"""

import sqlite3
import os

DATABASE_PATH = "brand_visibility.db"

def migrate_database():
    """Add industry column to analysis_sessions table"""
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database not found at: {DATABASE_PATH}")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if industry column already exists
        cursor.execute("PRAGMA table_info(analysis_sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'industry' in columns:
            print("✅ 'industry' column already exists. No migration needed.")
            return
        
        # Add industry column
        print("🔄 Adding 'industry' column to analysis_sessions table...")
        cursor.execute('''
            ALTER TABLE analysis_sessions 
            ADD COLUMN industry TEXT
        ''')
        
        conn.commit()
        print("✅ Migration successful! 'industry' column added.")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(analysis_sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current columns: {', '.join(columns)}")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Migration error: {str(e)}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DATABASE MIGRATION - Add Industry Column")
    print("="*60 + "\n")
    
    migrate_database()
    
    print("\n" + "="*60)
    print("Migration Complete")
    print("="*60 + "\n")