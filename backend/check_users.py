import sys
sys.path.insert(0, '.')
from database import SessionLocal
from sqlalchemy import text
import bcrypt

db = SessionLocal()

# Get all users
result = db.execute(text("SELECT id, ad_soyad, email, rol FROM users ORDER BY id"))
users = result.fetchall()

print("=" * 70)
print("KAYITLI KULLANICILAR")
print("=" * 70)
for u in users:
    print(f"ID: {u[0]} | {u[1]} | {u[2]} | {u[3]}")

print("=" * 70)

# Check for admin
result = db.execute(text("SELECT id FROM users WHERE rol = 'ADMIN'"))
admin = result.fetchone()

if not admin:
    print("\nAdmin bulunamadi, olusturuluyor...")
    password = '123456'
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    db.execute(text("""
        INSERT INTO users (ad_soyad, email, password_hash, rol, is_active, created_at)
        VALUES ('Admin User', 'admin@test.com', :hash, 'ADMIN', true, NOW())
    """), {'hash': hashed})
    db.commit()
    print("Admin olusturuldu!")

print("\nGiris bilgileri:")
print("  Email: admin@test.com")
print("  Sifre: 123456")
print()

db.close()
