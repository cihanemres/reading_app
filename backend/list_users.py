import sys
sys.path.insert(0, '.')
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text("SELECT id, ad_soyad, email, rol FROM users ORDER BY id"))
users = result.fetchall()

for u in users:
    print(f"{u[0]}|{u[1]}|{u[2]}|{u[3]}")

db.close()
