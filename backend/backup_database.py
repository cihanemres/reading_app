"""
Database Backup Script
Run this script to backup the PostgreSQL database
"""
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def backup_database():
    """
    Create a backup of the PostgreSQL database
    
    Usage:
        python backup_database.py
    
    The backup will be saved to backups/ directory with timestamp
    """
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    # Create backups directory
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
    
    print(f"📦 Creating database backup...")
    print(f"   Output: {backup_file}")
    
    try:
        # For Render PostgreSQL, use pg_dump
        # Parse the DATABASE_URL
        # Format: postgresql://user:password@host:port/database
        
        if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
            # Use pg_dump for PostgreSQL
            result = subprocess.run(
                ['pg_dump', database_url, '-f', backup_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                file_size = os.path.getsize(backup_file)
                print(f"✅ Backup created successfully!")
                print(f"   Size: {file_size / 1024:.2f} KB")
                return True
            else:
                print(f"❌ Backup failed: {result.stderr}")
                return False
        else:
            print("❌ Unsupported database type. Only PostgreSQL is supported.")
            return False
            
    except FileNotFoundError:
        print("❌ pg_dump not found. Please install PostgreSQL client tools.")
        print("   On Windows: https://www.postgresql.org/download/windows/")
        print("   On Mac: brew install postgresql")
        print("   On Linux: apt-get install postgresql-client")
        return False
    except Exception as e:
        print(f"❌ Backup failed with error: {e}")
        return False

def list_backups():
    """List all available backups"""
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    
    if not os.path.exists(backup_dir):
        print("No backups found.")
        return []
    
    backups = [f for f in os.listdir(backup_dir) if f.endswith('.sql')]
    backups.sort(reverse=True)
    
    print(f"📋 Available backups ({len(backups)}):")
    for backup in backups:
        path = os.path.join(backup_dir, backup)
        size = os.path.getsize(path) / 1024
        print(f"   - {backup} ({size:.2f} KB)")
    
    return backups

def restore_database(backup_file: str):
    """
    Restore database from a backup file
    
    WARNING: This will overwrite all existing data!
    
    Args:
        backup_file: Path to the backup SQL file
    """
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    confirm = input("⚠️  This will OVERWRITE all existing data. Are you sure? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Restore cancelled.")
        return False
    
    print(f"🔄 Restoring database from {backup_file}...")
    
    try:
        result = subprocess.run(
            ['psql', database_url, '-f', backup_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Database restored successfully!")
            return True
        else:
            print(f"❌ Restore failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ psql not found. Please install PostgreSQL client tools.")
        return False
    except Exception as e:
        print(f"❌ Restore failed with error: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'backup':
            backup_database()
        elif command == 'list':
            list_backups()
        elif command == 'restore' and len(sys.argv) > 2:
            restore_database(sys.argv[2])
        else:
            print("Usage:")
            print("  python backup_database.py backup  - Create a new backup")
            print("  python backup_database.py list    - List available backups")
            print("  python backup_database.py restore <file>  - Restore from backup")
    else:
        # Default: create backup
        backup_database()
