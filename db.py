import os
import re
import json
import sqlite3
import datetime
from flask import request
from werkzeug.security import generate_password_hash
from config import Config

try:
    import firebase_admin
    from firebase_admin import credentials, db as firebase_db
except ImportError:
    firebase_admin = None

# Daftar seluruh tabel sistem
TABLES = [
    'pengaturan', 'users', 'kategori', 'bahan_baku', 'menu_item',
    'menu_resep', 'log_stok_bahan', 'pelanggan_member', 'transaksi',
    'detail_transaksi', 'log_aktivitas'
]

# Inisialisasi Firebase Admin SDK
_firebase_ready = False
if firebase_admin:
    cred_json = os.environ.get("FIREBASE_CREDENTIALS")
    db_url = Config.FIREBASE_DATABASE_URL
    try:
        if cred_json and not firebase_admin._apps:
            cred_dict = json.loads(cred_json)
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
            _firebase_ready = True
        elif firebase_admin._apps:
            _firebase_ready = True
    except Exception as e:
        print(f"[FIREBASE INIT ERROR] {e}")


def translate_mysql_to_sqlite(sql):
    """Menerjemahkan sintaks spesifik MySQL di app.py agar jalan sempurna di SQLite."""
    # 1. Parameter %s menjadi ?
    sql = sql.replace('%s', '?')
    
    # 2. DATE_SUB(CURDATE(), INTERVAL 6 DAY) -> date('now', '+7 hours', '-6 day')
    sql = re.sub(
        r"DATE_SUB\(\s*CURDATE\(\)\s*,\s*INTERVAL\s+(\d+)\s+DAY\s*\)",
        r"date('now', '+7 hours', '-\1 day')",
        sql,
        flags=re.IGNORECASE
    )
    
    # 3. CURDATE() -> tanggal hari ini WIB
    sql = re.sub(r"CURDATE\(\)", "date('now', '+7 hours')", sql, flags=re.IGNORECASE)
    
    # 4. Tangani CONCAT(...) meskipun di dalam string terdapat tanda kurung seperti ' ('
    def repl_concat(match):
        inner = match.group(1)
        # Pisahkan berdasarkan koma yang berada di luar tanda kutip
        parts = re.split(r",\s*(?=(?:[^']*'[^']*')*[^']*$)", inner)
        return "(" + " || ".join(p.strip() for p in parts) + ")"

    sql = re.sub(
        r"(?<!GROUP_)CONCAT\(((?:[^()'']|'[^']*')+)\)",
        repl_concat,
        sql,
        flags=re.IGNORECASE
    )
    
    # 5. GROUP_CONCAT(expr SEPARATOR sep) -> GROUP_CONCAT(expr, sep)
    sql = re.sub(
        r"GROUP_CONCAT\((.+?)\s+SEPARATOR\s+('[^']*')\)",
        r"GROUP_CONCAT(\1, \2)",
        sql,
        flags=re.IGNORECASE | re.DOTALL
    )
    return sql

    """Menerjemahkan sintaks spesifik MySQL di app.py agar jalan di engine SQLite."""
    # 1. Parameter %s menjadi ?
    sql = sql.replace('%s', '?')
    # 2. DATE_SUB(CURDATE(), INTERVAL 6 DAY) -> date('now', '-6 day')
    sql = re.sub(
        r"DATE_SUB\(\s*CURDATE\(\)\s*,\s*INTERVAL\s+(\d+)\s+DAY\s*\)",
        r"date('now', '+7 hours', '-\1 day')",
        sql,
        flags=re.IGNORECASE
    )
    # 3. CURDATE() -> tanggal hari ini WIB
    sql = re.sub(r"CURDATE\(\)", "date('now', '+7 hours')", sql, flags=re.IGNORECASE)
    # 4. CONCAT(a, b, c) -> (a || b || c)
    def repl_concat(match):
        inner = match.group(1)
        parts = [p.strip() for p in inner.split(',')]
        return "(" + " || ".join(parts) + ")"
    sql = re.sub(r"CONCAT\(([^()]+)\)", repl_concat, sql, flags=re.IGNORECASE)
    # 5. GROUP_CONCAT(expr SEPARATOR sep) -> GROUP_CONCAT(expr, sep)
    sql = re.sub(
        r"GROUP_CONCAT\((.+?)\s+SEPARATOR\s+('[^']*')\)",
        r"GROUP_CONCAT(\1, \2)",
        sql,
        flags=re.IGNORECASE
    )
    return sql


class CursorWrapper:
    def __init__(self, raw_cursor):
        self.raw_cursor = raw_cursor
        self.lastrowid = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.raw_cursor.close()

    def execute(self, query, args=()):
        q_Check = query.strip().upper()
        if q_Check.startswith("SHOW CREATE TABLE"):
            tbl = query.split("`")[1] if "`" in query else "table"
            self._mock_rows = [{'Create Table': f"-- Struktur Tabel {tbl}"}]
            return

        sql = translate_mysql_to_sqlite(query)
        if args is None:
            args = ()
        elif not isinstance(args, (list, tuple)):
            args = (args,)

        self.raw_cursor.execute(sql, tuple(args))
        self.lastrowid = self.raw_cursor.lastrowid
        self.rowcount = self.raw_cursor.rowcount
        self._mock_rows = None

    def fetchall(self):
        if getattr(self, '_mock_rows', None) is not None:
            return self._mock_rows
        rows = self.raw_cursor.fetchall()
        return [dict(r) for r in rows]

    def fetchone(self):
        if getattr(self, '_mock_rows', None) is not None:
            return self._mock_rows[0] if self._mock_rows else None
        row = self.raw_cursor.fetchone()
        return dict(row) if row else None


class ConnectionWrapper:
    def __init__(self, raw_conn):
        self.raw_conn = raw_conn

    def cursor(self):
        return CursorWrapper(self.raw_conn.cursor())

    def commit(self):
        self.raw_conn.commit()
        sync_sqlite_to_firebase(self.raw_conn)

    def rollback(self):
        self.raw_conn.rollback()

    def close(self):
        pass  # Biarkan koneksi memori tetap hidup selama instance aktif


_raw_sqlite_conn = None


def init_sqlite_schema(conn):
    """Membuat tabel-tabel dan data awal jika belum ada."""
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS pengaturan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_toko TEXT, slogan TEXT, no_telepon TEXT, email TEXT,
            alamat TEXT, pesan_struk_header TEXT, pesan_struk_footer TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, email TEXT, password TEXT, nama_lengkap TEXT, role TEXT
        );
        CREATE TABLE IF NOT EXISTS kategori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_kategori TEXT, deskripsi TEXT
        );
        CREATE TABLE IF NOT EXISTS bahan_baku (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_bahan TEXT, satuan TEXT, stok REAL DEFAULT 0,
            stok_minimal REAL DEFAULT 5, harga_satuan REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS menu_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategori_id INTEGER, kode_menu TEXT, nama_menu TEXT,
            deskripsi TEXT, harga REAL DEFAULT 0, status TEXT DEFAULT 'Tersedia', gambar TEXT
        );
        CREATE TABLE IF NOT EXISTS menu_resep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER, bahan_id INTEGER, jumlah_pakai REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS log_stok_bahan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bahan_id INTEGER, jenis TEXT, jumlah REAL,
            stok_sebelum REAL, stok_sesudah REAL, keterangan TEXT,
            created_at TEXT DEFAULT (datetime('now', '+7 hours'))
        );
        CREATE TABLE IF NOT EXISTS pelanggan_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_member TEXT, nama TEXT, no_telp TEXT, email TEXT, alamat TEXT, poin INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no_transaksi TEXT, no_antrean TEXT, tanggal TEXT, member_id INTEGER,
            nama_pelanggan TEXT, total_item INTEGER DEFAULT 0, subtotal REAL DEFAULT 0,
            diskon REAL DEFAULT 0, pajak REAL DEFAULT 0, total_akhir REAL DEFAULT 0,
            metode_pembayaran TEXT, bayar REAL DEFAULT 0, kembalian REAL DEFAULT 0,
            status_antrean TEXT DEFAULT 'Menunggu', catatan TEXT,
            created_at TEXT DEFAULT (datetime('now', '+7 hours'))
        );
        CREATE TABLE IF NOT EXISTS detail_transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaksi_id INTEGER, menu_id INTEGER, nama_menu TEXT,
            jumlah INTEGER DEFAULT 1, harga_satuan REAL DEFAULT 0,
            subtotal REAL DEFAULT 0, catatan_item TEXT
        );
        CREATE TABLE IF NOT EXISTS log_aktivitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, username TEXT, aktivitas TEXT, detail TEXT, ip_address TEXT,
            created_at TEXT DEFAULT (datetime('now', '+7 hours'))
        );
    """)
    conn.commit()


def load_firebase_to_sqlite(conn):
    """Menarik data dari Firebase Realtime Database ke SQLite saat startup."""
    c = conn.cursor()
    if _firebase_ready:
        try:
            root_data = firebase_db.reference('/').get() or {}
            # 1. Muat tabel standar jika sudah ada di node _sql_tables Firebase
            sql_tables = root_data.get('_sql_tables', {})
            for tbl in TABLES:
                rows = sql_tables.get(tbl, [])
                if isinstance(rows, dict):
                    rows = list(rows.values())
                if rows:
                    cols = list(rows[0].keys())
                    placeholders = ", ".join(["?"] * len(cols))
                    col_names = ", ".join(cols)
                    for r in rows:
                        vals = [r.get(k) for k in cols]
                        c.execute(f"INSERT OR REPLACE INTO {tbl} ({col_names}) VALUES ({placeholders})", vals)

            # 2. Jika menu_item masih kosong tapi ada node 'menu' lama di Firebase kamu
            c.execute("SELECT COUNT(*) as cnt FROM menu_item")
            if c.fetchone()['cnt'] == 0 and 'menu' in root_data:
                raw_menus = root_data['menu']
                items = raw_menus.values() if isinstance(raw_menus, dict) else raw_menus
                for idx, m in enumerate(items, 1):
                    if not isinstance(m, dict):
                        continue
                    nama = m.get('nama_menu') or m.get('nama') or f"Es Teler {idx}"
                    harga = float(m.get('harga', 15000))
                    deskripsi = m.get('deskripsi', 'Segar dan nikmat')
                    gambar = m.get('gambar', 'default_menu.jpg')
                    c.execute("""
                        INSERT INTO menu_item (id, kategori_id, kode_menu, nama_menu, deskripsi, harga, status, gambar)
                        VALUES (?, 1, ?, ?, ?, ?, 'Tersedia', ?)
                    """, (idx, f"MN-{idx:03d}", nama, deskripsi, harga, gambar))
        except Exception as e:
            print(f"[FIREBASE LOAD WARNING] {e}")

    # Pastikan data Pengaturan Kedai ada
    c.execute("SELECT COUNT(*) as cnt FROM pengaturan")
    if c.fetchone()['cnt'] == 0:
        c.execute("""
            INSERT INTO pengaturan (id, nama_toko, slogan, no_telepon, email, alamat, pesan_struk_header, pesan_struk_footer)
            VALUES (1, 'Kedai Unik', 'Sensasi Kesegaran Asli Buah Nusantara', '0812-3456-7890', 'admin@estelerpos.my.id', 'Jl. Boulevard Hijau No. 77', 'Selamat Datang di Kedai Unik', 'Terima kasih atas kunjungan Anda!')
        """)

    # Pastikan Kategori Default ada
    c.execute("SELECT COUNT(*) as cnt FROM kategori")
    if c.fetchone()['cnt'] == 0:
        c.execute("INSERT INTO kategori (id, nama_kategori, deskripsi) VALUES (1, 'Es Teler Spesial', 'Varian Es Teler Utama')")
        c.execute("INSERT INTO kategori (id, nama_kategori, deskripsi) VALUES (2, 'Topping & Ekstra', 'Tambahan Topping Pilihan')")

    # Pastikan Akun Admin Default ada (admin / admin123)
    c.execute("SELECT COUNT(*) as cnt FROM users")
    if c.fetchone()['cnt'] == 0:
        hashed_pw = generate_password_hash('admin123')
        c.execute("""
            INSERT INTO users (id, username, email, password, nama_lengkap, role)
            VALUES (1, 'admin', 'admin@estelerpos.my.id', ?, 'Administrator Kedai Unik', 'Admin')
        """, (hashed_pw,))

    conn.commit()


def sync_sqlite_to_firebase(conn):
    """Menyimpan perubahan dari SQLite kembali ke Firebase Realtime Database."""
    if not _firebase_ready:
        return
    try:
        c = conn.cursor()
        payload = {}
        for tbl in TABLES:
            c.execute(f"SELECT * FROM {tbl}")
            payload[tbl] = [dict(r) for r in c.fetchall()]
        firebase_db.reference('_sql_tables').set(payload)
    except Exception as e:
        print(f"[FIREBASE SYNC WARNING] {e}")


def get_db_connection():
    """Membuka koneksi database yang sudah terhubung dengan Firebase."""
    global _raw_sqlite_conn
    if _raw_sqlite_conn is None:
        _raw_sqlite_conn = sqlite3.connect(':memory:', check_same_thread=False)
        _raw_sqlite_conn.row_factory = sqlite3.Row
        init_sqlite_schema(_raw_sqlite_conn)
        load_firebase_to_sqlite(_raw_sqlite_conn)
        sync_sqlite_to_firebase(_raw_sqlite_conn)
    return ConnectionWrapper(_raw_sqlite_conn)


def query_db(query, args=(), one=False):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(query, args)
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv


def execute_db(query, args=(), return_id=False):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(query, args)
        conn.commit()
        if return_id:
            return cursor.lastrowid
        return cursor.rowcount


def log_activity(user_id, username, aktivitas, detail=''):
    try:
        ip = request.remote_addr if request else '127.0.0.1'
        query = """
            INSERT INTO log_aktivitas (user_id, username, aktivitas, detail, ip_address)
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_db(query, (user_id, username, aktivitas, detail, ip))
    except Exception as e:
        print(f"[LOG ERROR] {e}")


def get_next_queue_number():
    today_count_query = "SELECT COUNT(*) as count FROM transaksi WHERE tanggal = CURDATE()"
    res = query_db(today_count_query, one=True)
    next_num = (res['count'] if res else 0) + 1
    return f"A-{next_num:03d}"


def get_next_trx_number():
    today_str = datetime.date.today().strftime('%Y%m%d')
    today_count_query = "SELECT COUNT(*) as count FROM transaksi WHERE tanggal = CURDATE()"
    res = query_db(today_count_query, one=True)
    next_num = (res['count'] if res else 0) + 1
    return f"TRX-{today_str}-{next_num:03d}"


def deduct_raw_materials_for_transaction(cart_items, trx_no=""):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for item in cart_items:
                menu_id = item['menu_id']
                qty = float(item['qty'])
                cursor.execute("""
                    SELECT mr.bahan_id, mr.jumlah_pakai, b.nama_bahan, b.stok, b.satuan
                    FROM menu_resep mr
                    JOIN bahan_baku b ON mr.bahan_id = b.id
                    WHERE mr.menu_id = %s
                """, (menu_id,))
                resep_list = cursor.fetchall()

                for resep in resep_list:
                    bahan_id = resep['bahan_id']
                    pemakaian_total = float(resep['jumlah_pakai']) * qty
                    stok_sekarang = float(resep['stok'])
                    stok_baru = max(0.0, stok_sekarang - pemakaian_total)

                    cursor.execute("UPDATE bahan_baku SET stok = %s WHERE id = %s", (stok_baru, bahan_id))
                    cursor.execute("""
                        INSERT INTO log_stok_bahan 
                        (bahan_id, jenis, jumlah, stok_sebelum, stok_sesudah, keterangan)
                        VALUES (%s, 'Keluar', %s, %s, %s, %s)
                    """, (
                        bahan_id, pemakaian_total, stok_sekarang, stok_baru,
                        f"Pengurangan otomatis transaksi {trx_no} ({item.get('nama_menu', '')} x{qty})"
                    ))
        conn.commit()
    except Exception as e:
        print(f"[STOCK DEDUCTION ERROR] {e}")
        conn.rollback()