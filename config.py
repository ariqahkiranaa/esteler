import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Secret Key untuk Flask Session
    SECRET_KEY = os.getenv('SECRET_KEY', 'es_teler_juara_super_secret_key_2026')
    
    # Konfigurasi Firebase Realtime Database
    FIREBASE_DATABASE_URL = os.getenv(
        'FIREBASE_DATABASE_URL', 
        'https://es-teler-default-rtdb.firebaseio.com/'
    )
    
    # Konfigurasi Database MySQL (Jika suatu saat dipakai lokal)
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'db_penjualan_esteler')
    
    # Konfigurasi Upload Gambar (Otomatis ke /tmp jika di Vercel)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    if os.environ.get('VERCEL') or not os.access(BASE_DIR, os.W_OK):
        UPLOAD_FOLDER = '/tmp/uploads'
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
        
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max 16 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    
    # Port Aplikasi Flask
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')