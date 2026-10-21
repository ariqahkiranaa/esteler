import pymysql
import pymysql.cursors
from config import Config
from flask import request

def get_db_connection():
    """Membuka koneksi ke database MySQL."""
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        charset='utf8mb4'
    )

def query_db(query, args=(), one=False):
    """Menjalankan query SELECT dan mengembalikan hasil (list of dict atau single dict)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

def execute_db(query, args=(), return_id=False):
    """Menjalankan query INSERT/UPDATE/DELETE dan mengembalikan last_insert_id atau rowcount."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            conn.commit()
            if return_id:
                return cursor.lastrowid
            return cursor.rowcount
    finally:
        conn.close()

def log_activity(user_id, username, aktivitas, detail=''):
    """Mencatat aktivitas admin ke dalam tabel log_aktivitas."""
    try:
        ip = request.remote_addr if request else '127.0.0.1'
        query = """
            INSERT INTO log_aktivitas (user_id, username, aktivitas, detail, ip_address)
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_db(query, (user_id, username, aktivitas, detail, ip))
    except Exception as e:
        print(f"[LOG ERROR] Gagal mencatat log aktivitas: {e}")

def get_next_queue_number():
    """Menghasilkan nomor antrean berikutnya untuk hari ini (misal A-001, A-002)."""
    today_count_query = """
        SELECT COUNT(*) as count FROM transaksi WHERE tanggal = CURDATE()
    """
    res = query_db(today_count_query, one=True)
    next_num = (res['count'] if res else 0) + 1
    return f"A-{next_num:03d}"

def get_next_trx_number():
    """Menghasilkan nomor transaksi unik (misal TRX-20261020-001)."""
    import datetime
    today_str = datetime.date.today().strftime('%Y%m%d')
    today_count_query = """
        SELECT COUNT(*) as count FROM transaksi WHERE tanggal = CURDATE()
    """
    res = query_db(today_count_query, one=True)
    next_num = (res['count'] if res else 0) + 1
    return f"TRX-{today_str}-{next_num:03d}"

def deduct_raw_materials_for_transaction(cart_items, trx_no=""):
    """
    Mengurangi stok bahan baku secara otomatis berdasarkan tabel resep (menu_resep)
    untuk setiap item menu yang dipesan, dan mencatat mutasi stok keluar.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for item in cart_items:
                menu_id = item['menu_id']
                qty = float(item['qty'])
                
                # Cari resep untuk menu ini
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
                    
                    # Update stok bahan
                    cursor.execute("""
                        UPDATE bahan_baku
                        SET stok = %s
                        WHERE id = %s
                    """, (stok_baru, bahan_id))
                    
                    # Catat log mutasi stok
                    cursor.execute("""
                        INSERT INTO log_stok_bahan 
                        (bahan_id, jenis, jumlah, stok_sebelum, stok_sesudah, keterangan)
                        VALUES (%s, 'Keluar', %s, %s, %s, %s)
                    """, (
                        bahan_id,
                        pemakaian_total,
                        stok_sekarang,
                        stok_baru,
                        f"Pengurangan otomatis transaksi {trx_no} ({item.get('nama_menu', '')} x{qty})"
                    ))
        conn.commit()
    except Exception as e:
        print(f"[STOCK DEDUCTION ERROR] {e}")
        conn.rollback()
    finally:
        conn.close()
