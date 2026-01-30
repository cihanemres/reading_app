"""
Approve admin user in SQLite database
Uses direct SQLite connection to avoid model import issues
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'okuma.db')
print(f"Database path: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Show all users
cursor.execute("SELECT id, email, rol, is_approved FROM users")
users = cursor.fetchall()
print("\nAll users:")
for u in users:
    print(f"  ID:{u[0]} | {u[1]} | {u[2]} | Approved:{u[3]}")

# Approve all admin users
cursor.execute("UPDATE users SET is_approved = 1 WHERE email = 'admin@test.com'")
conn.commit()
print("\nAdmin user approved!")

conn.close()
