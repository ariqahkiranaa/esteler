import os
import datetime
from io import BytesIO
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, g, send_file, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from config import Config
from db import (
    get_db_connection, query_db, execute_db, log_activity,
    get_next_queue_number, get_next_trx_number,
    deduct_raw_materials_for_transaction
)

app = Flask(__name__)
app.config.from_object(Config)

# Pastikan folder upload ada
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper: Allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Decorator: Login Required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu untuk mengakses sistem.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Hook: Sebelum Setiap Request
@app.before_request
def before_request():
    # Ambil pengaturan kedai
    try:
        g.shop = query_db("SELECT * FROM pengaturan WHERE id = 1", one=True)
    except Exception:
        g.shop = {
            'nama_toko': 'Kedai Es Teler Juara 77',
            'slogan': 'Sensasi Kesegaran Asli Buah Nusantara',
            'alamat': 'Jl. Boulevard Hijau No. 77',
            'no_telepon': '0812-3456-7890'
        }

    # Ambil alert bahan baku yang menipis
    try:
        low_items = query_db("""
            SELECT id, nama_bahan, satuan, stok, stok_minimal
            FROM bahan_baku
            WHERE stok <= stok_minimal
            ORDER BY stok ASC
        """)
        g.low_stock_items = low_items or []
        g.low_stock_count = len(g.low_stock_items)
    except Exception:
        g.low_stock_items = []
        g.low_stock_count = 0

    # Ambil jumlah antrean aktif hari ini (Menunggu & Diproses)
    try:
        active_q = query_db("""
            SELECT COUNT(*) as cnt
            FROM transaksi
            WHERE tanggal = CURDATE() AND status_antrean IN ('Menunggu', 'Diproses')
        """, one=True)
        g.antrean_aktif_count = active_q['cnt'] if active_q else 0
    except Exception:
        g.antrean_aktif_count = 0

# ========================================================
# 1. AUTENTIKASI (LOGIN & LOGOUT)
# ========================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '').strip()

        user = query_db("""
            SELECT * FROM users
            WHERE username = %s OR email = %s
        """, (username_or_email, username_or_email), one=True)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_nama'] = user['nama_lengkap']
            session['role'] = user['role']

            log_activity(user['id'], user['username'], 'Login Admin', 'Berhasil login ke sistem')
            flash(f"Selamat datang kembali, {user['nama_lengkap']}!", 'success')

            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Username/email atau password yang Anda masukkan salah.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    uid = session.get('user_id')
    uname = session.get('username')
    if uid:
        log_activity(uid, uname, 'Logout Admin', 'Keluar dari sesi sistem')
    session.clear()
    flash('Anda telah berhasil keluar dari sistem.', 'info')
    return redirect(url_for('login'))

# ========================================================
# 2. DASHBOARD UTAMA
# ========================================================

@app.route('/')
@login_required
def dashboard():
    # 1. Total Omset Hari Ini
    omset_today = query_db("""
        SELECT SUM(total_akhir) as total
        FROM transaksi
        WHERE tanggal = CURDATE() AND status_antrean != 'Dibatalkan'
    """, one=True)
    omset_val = omset_today['total'] if omset_today and omset_today['total'] else 0

    # 2. Total Transaksi Hari Ini
    trx_today = query_db("""
        SELECT COUNT(*) as cnt
        FROM transaksi
        WHERE tanggal = CURDATE()
    """, one=True)
    trx_count = trx_today['cnt'] if trx_today else 0

    # 3. Transaksi Terakhir Hari Ini (Limit 7)
    recent_trx = query_db("""
        SELECT id, no_transaksi, no_antrean, nama_pelanggan, total_akhir, metode_pembayaran, status_antrean, created_at
        FROM transaksi
        WHERE tanggal = CURDATE()
        ORDER BY id DESC
        LIMIT 7
    """)

    # 4. Top Menu Terlaris (Hari Ini / Minggu Ini)
    top_menus = query_db("""
        SELECT m.nama_menu, SUM(dt.jumlah) as total_terjual, SUM(dt.subtotal) as total_omset
        FROM detail_transaksi dt
        JOIN transaksi t ON dt.transaksi_id = t.id
        JOIN menu_item m ON dt.menu_id = m.id
        WHERE t.status_antrean != 'Dibatalkan'
        GROUP BY dt.menu_id, m.nama_menu
        ORDER BY total_terjual DESC
        LIMIT 5
    """)

    # 5. Data Grafik Omset 7 Hari Terakhir
    sales_rows = query_db("""
        SELECT tanggal, COALESCE(SUM(total_akhir), 0) as omset
        FROM transaksi
        WHERE tanggal >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
          AND status_antrean != 'Dibatalkan'
        GROUP BY tanggal
        ORDER BY tanggal ASC
    """)

    # Siapkan map 7 hari terakhir agar hari tanpa transaksi tetap bernilai 0
    days_map = {}
    for i in range(6, -1, -1):
        d = datetime.date.today() - datetime.timedelta(days=i)
        days_map[d.strftime('%Y-%m-%d')] = {
            'label': d.strftime('%d %b'),
            'omset': 0.0
        }

    if sales_rows:
        for r in sales_rows:
            key = str(r['tanggal'])
            if key in days_map:
                days_map[key]['omset'] = float(r['omset'])

    chart_labels = [v['label'] for v in days_map.values()]
    chart_data = [v['omset'] for v in days_map.values()]

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        omset_hari_ini=omset_val,
        transaksi_hari_ini_count=trx_count,
        antrean_aktif_count=g.antrean_aktif_count,
        low_stock_count=g.low_stock_count,
        low_stock_items=g.low_stock_items,
        recent_transactions=recent_trx,
        top_menus=top_menus,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

# ========================================================
# 3. MANAJEMEN MENU & KATEGORI
# ========================================================

@app.route('/es_teler_pos')
@login_required
def menu_page():
    search_q = request.args.get('q', '').strip()
    selected_cat = request.args.get('cat', '').strip()

    sql = """
        SELECT m.*, k.nama_kategori
        FROM menu_item m
        JOIN kategori k ON m.kategori_id = k.id
        WHERE 1=1
    """
    params = []

    if search_q:
        sql += " AND (m.nama_menu LIKE %s OR m.kode_menu LIKE %s)"
        params.extend([f"%{search_q}%", f"%{search_q}%"])

    if selected_cat:
        sql += " AND m.kategori_id = %s"
        params.append(selected_cat)

    sql += " ORDER BY m.id DESC"
    menus = query_db(sql, params)

    # Categories with count of items
    categories = query_db("""
        SELECT k.*, COUNT(m.id) as total_items
        FROM kategori k
        LEFT JOIN menu_item m ON k.id = m.kategori_id
        GROUP BY k.id
        ORDER BY k.id ASC
    """)

    all_raw_materials = query_db("SELECT id, nama_bahan, satuan FROM bahan_baku ORDER BY nama_bahan ASC")
    total_menu_count = len(query_db("SELECT id FROM menu_item"))

    # Auto next kode menu
    next_num = total_menu_count + 1
    auto_kode_menu = f"MN-{next_num:03d}"

    return render_template(
        'menu.html',
        active_page='menu',
        menus=menus,
        categories=categories,
        all_raw_materials=all_raw_materials,
        total_menu_count=total_menu_count,
        auto_kode_menu=auto_kode_menu,
        search_query=search_q,
        selected_cat=selected_cat
    )

@app.route('/es_teler_pos/menu/tambah', methods=['POST'])
@login_required
def menu_tambah():
    kode_menu = request.form.get('kode_menu', '').strip().upper()
    kategori_id = request.form.get('kategori_id')
    nama_menu = request.form.get('nama_menu', '').strip()
    harga = float(request.form.get('harga', 0))
    status = request.form.get('status', 'Tersedia')
    deskripsi = request.form.get('deskripsi', '').strip()

    # Upload Foto
    foto_filename = 'default_menu.jpg'
    file = request.files.get('foto')
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(f"menu_{kode_menu}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        foto_filename = filename

    try:
        execute_db("""
            INSERT INTO menu_item (kategori_id, kode_menu, nama_menu, deskripsi, harga, status, gambar)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (kategori_id, kode_menu, nama_menu, deskripsi, harga, status, foto_filename))

        log_activity(session['user_id'], session['username'], 'Tambah Menu', f"Menambah menu baru: {nama_menu} ({kode_menu})")
        flash(f"Menu '{nama_menu}' berhasil ditambahkan!", 'success')
    except Exception as e:
        flash(f"Gagal menambahkan menu: {e}", 'danger')

    return redirect(url_for('menu_page'))

@app.route('/menu/edit/<int:id>', methods=['POST'])
@login_required
def menu_edit(id):
    kode_menu = request.form.get('kode_menu', '').strip().upper()
    kategori_id = request.form.get('kategori_id')
    nama_menu = request.form.get('nama_menu', '').strip()
    harga = float(request.form.get('harga', 0))
    status = request.form.get('status', 'Tersedia')
    deskripsi = request.form.get('deskripsi', '').strip()

    file = request.files.get('foto')
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(f"menu_{kode_menu}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        execute_db("""
            UPDATE menu_item
            SET kategori_id=%s, kode_menu=%s, nama_menu=%s, deskripsi=%s, harga=%s, status=%s, gambar=%s
            WHERE id=%s
        """, (kategori_id, kode_menu, nama_menu, deskripsi, harga, status, filename, id))
    else:
        execute_db("""
            UPDATE menu_item
            SET kategori_id=%s, kode_menu=%s, nama_menu=%s, deskripsi=%s, harga=%s, status=%s
            WHERE id=%s
        """, (kategori_id, kode_menu, nama_menu, deskripsi, harga, status, id))

    log_activity(session['user_id'], session['username'], 'Edit Menu', f"Memperbarui menu: {nama_menu} (ID: {id})")
    flash(f"Menu '{nama_menu}' berhasil diperbarui!", 'success')
    return redirect(url_for('menu_page'))

@app.route('/menu/hapus/<int:id>', methods=['POST'])
@login_required
def menu_hapus(id):
    m = query_db("SELECT nama_menu FROM menu_item WHERE id = %s", (id,), one=True)
    if m:
        execute_db("DELETE FROM menu_item WHERE id = %s", (id,))
        log_activity(session['user_id'], session['username'], 'Hapus Menu', f"Menghapus menu: {m['nama_menu']} (ID: {id})")
        flash(f"Menu '{m['nama_menu']}' berhasil dihapus.", 'info')
    return redirect(url_for('menu_page'))

# Kategori CRUD
@app.route('/kategori/tambah', methods=['POST'])
@login_required
def kategori_tambah():
    nama = request.form.get('nama_kategori', '').strip()
    deskripsi = request.form.get('deskripsi', '').strip()
    if nama:
        execute_db("INSERT INTO kategori (nama_kategori, deskripsi) VALUES (%s, %s)", (nama, deskripsi))
        log_activity(session['user_id'], session['username'], 'Tambah Kategori', f"Menambah kategori: {nama}")
        flash(f"Kategori '{nama}' berhasil dibuat!", 'success')
    return redirect(url_for('menu_page'))

@app.route('/kategori/hapus/<int:id>', methods=['POST'])
@login_required
def kategori_hapus(id):
    execute_db("DELETE FROM kategori WHERE id = %s", (id,))
    flash('Kategori berhasil dihapus.', 'info')
    return redirect(url_for('menu_page'))

# Resep Bahan Baku API
@app.route('/api/menu/<int:id>/resep')
@login_required
def api_menu_resep(id):
    resep = query_db("""
        SELECT mr.id, mr.jumlah_pakai, b.nama_bahan, b.satuan
        FROM menu_resep mr
        JOIN bahan_baku b ON mr.bahan_id = b.id
        WHERE mr.menu_id = %s
    """, (id,))
    return jsonify(resep or [])

@app.route('/resep/tambah', methods=['POST'])
@login_required
def resep_tambah():
    menu_id = request.form.get('menu_id')
    bahan_id = request.form.get('bahan_id')
    jumlah_pakai = float(request.form.get('jumlah_pakai', 0))

    if menu_id and bahan_id and jumlah_pakai > 0:
        execute_db("""
            INSERT INTO menu_resep (menu_id, bahan_id, jumlah_pakai)
            VALUES (%s, %s, %s)
        """, (menu_id, bahan_id, jumlah_pakai))
        flash('Komposisi bahan berhasil ditautkan ke menu!', 'success')
    return redirect(url_for('menu_page'))

@app.route('/resep/hapus/<int:id>', methods=['POST'])
@login_required
def resep_hapus(id):
    execute_db("DELETE FROM menu_resep WHERE id = %s", (id,))
    flash('Bahan berhasil dilepas dari resep menu.', 'info')
    return redirect(url_for('menu_page'))

# ========================================================
# 4. MANAJEMEN STOK BAHAN BAKU
# ========================================================

@app.route('/stok')
@login_required
def stok_page():
    raw_materials = query_db("SELECT * FROM bahan_baku ORDER BY nama_bahan ASC")
    stock_logs = query_db("""
        SELECT l.*, b.nama_bahan, b.satuan
        FROM log_stok_bahan l
        JOIN bahan_baku b ON l.bahan_id = b.id
        ORDER BY l.id DESC
        LIMIT 50
    """)
    return render_template(
        'stok.html',
        active_page='stok',
        raw_materials=raw_materials,
        stock_logs=stock_logs,
        low_stock_count=g.low_stock_count
    )

@app.route('/stok/tambah', methods=['POST'])
@login_required
def bahan_tambah():
    nama_bahan = request.form.get('nama_bahan', '').strip()
    satuan = request.form.get('satuan', '').strip()
    stok = float(request.form.get('stok', 0))
    stok_minimal = float(request.form.get('stok_minimal', 5))
    harga_satuan = float(request.form.get('harga_satuan', 0))

    bahan_id = execute_db("""
        INSERT INTO bahan_baku (nama_bahan, satuan, stok, stok_minimal, harga_satuan)
        VALUES (%s, %s, %s, %s, %s)
    """, (nama_bahan, satuan, stok, stok_minimal, harga_satuan), return_id=True)

    if stok > 0:
        execute_db("""
            INSERT INTO log_stok_bahan (bahan_id, jenis, jumlah, stok_sebelum, stok_sesudah, keterangan)
            VALUES (%s, 'Masuk', %s, 0, %s, 'Stok awal penambahan bahan baku baru')
        """, (bahan_id, stok, stok))

    log_activity(session['user_id'], session['username'], 'Tambah Bahan Baku', f"Menambah bahan: {nama_bahan} ({stok} {satuan})")
    flash(f"Bahan baku '{nama_bahan}' berhasil ditambahkan!", 'success')
    return redirect(url_for('stok_page'))

@app.route('/stok/edit/<int:id>', methods=['POST'])
@login_required
def bahan_edit(id):
    nama_bahan = request.form.get('nama_bahan', '').strip()
    satuan = request.form.get('satuan', '').strip()
    stok_minimal = float(request.form.get('stok_minimal', 5))
    harga_satuan = float(request.form.get('harga_satuan', 0))

    execute_db("""
        UPDATE bahan_baku
        SET nama_bahan=%s, satuan=%s, stok_minimal=%s, harga_satuan=%s
        WHERE id=%s
    """, (nama_bahan, satuan, stok_minimal, harga_satuan, id))

    log_activity(session['user_id'], session['username'], 'Edit Bahan Baku', f"Memperbarui data bahan: {nama_bahan}")
    flash(f"Data bahan baku '{nama_bahan}' berhasil disimpan!", 'success')
    return redirect(url_for('stok_page'))

@app.route('/stok/hapus/<int:id>', methods=['POST'])
@login_required
def bahan_hapus(id):
    b = query_db("SELECT nama_bahan FROM bahan_baku WHERE id=%s", (id,), one=True)
    if b:
        execute_db("DELETE FROM bahan_baku WHERE id=%s", (id,))
        log_activity(session['user_id'], session['username'], 'Hapus Bahan Baku', f"Menghapus bahan: {b['nama_bahan']}")
        flash(f"Bahan baku '{b['nama_bahan']}' berhasil dihapus.", 'info')
    return redirect(url_for('stok_page'))

@app.route('/stok/mutasi', methods=['POST'])
@login_required
def bahan_mutasi():
    bahan_id = int(request.form.get('bahan_id'))
    jenis = request.form.get('jenis', 'Masuk')
    jumlah = float(request.form.get('jumlah', 0))
    keterangan = request.form.get('keterangan', '').strip()

    bahan = query_db("SELECT * FROM bahan_baku WHERE id=%s", (bahan_id,), one=True)
    if not bahan or jumlah <= 0:
        flash("Data mutasi tidak valid.", "danger")
        return redirect(url_for('stok_page'))

    stok_sebelum = float(bahan['stok'])
    if jenis == 'Masuk':
        stok_sesudah = stok_sebelum + jumlah
    else:
        stok_sesudah = max(0.0, stok_sebelum - jumlah)

    execute_db("UPDATE bahan_baku SET stok=%s WHERE id=%s", (stok_sesudah, bahan_id))
    execute_db("""
        INSERT INTO log_stok_bahan (bahan_id, jenis, jumlah, stok_sebelum, stok_sesudah, keterangan)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (bahan_id, jenis, jumlah, stok_sebelum, stok_sesudah, keterangan or f"Mutasi manual {jenis}"))

    log_activity(session['user_id'], session['username'], 'Mutasi Stok', f"{jenis} {jumlah} {bahan['satuan']} {bahan['nama_bahan']}")
    flash(f"Mutasi {jenis} sebanyak {jumlah} {bahan['satuan']} untuk '{bahan['nama_bahan']}' berhasil dicatat!", 'success')
    return redirect(url_for('stok_page'))

# ========================================================
# 5. KASIR (POS) & SISTEM ANTREAN
# ========================================================

@app.route('/pos')
@login_required
def pos_page():
    menus = query_db("""
        SELECT m.*, k.nama_kategori
        FROM menu_item m
        JOIN kategori k ON m.kategori_id = k.id
        ORDER BY m.kategori_id ASC, m.nama_menu ASC
    """)
    categories = query_db("SELECT * FROM kategori ORDER BY id ASC")
    members = query_db("SELECT id, kode_member, nama, poin FROM pelanggan_member ORDER BY nama ASC")
    next_queue = get_next_queue_number()

    return render_template(
        'pos.html',
        active_page='pos',
        menus=menus,
        categories=categories,
        members=members,
        next_queue=next_queue
    )

@app.route('/api/transaksi/simpan', methods=['POST'])
@login_required
def api_simpan_transaksi():
    data = request.get_json()
    if not data or not data.get('items'):
        return jsonify({'status': 'error', 'message': 'Keranjang pesanan tidak boleh kosong'}), 400

    items = data['items']
    member_id = data.get('member_id')
    nama_pelanggan = data.get('nama_pelanggan', 'Pelanggan Umum').strip() or 'Pelanggan Umum'
    subtotal = float(data.get('subtotal', 0))
    diskon = float(data.get('diskon', 0))
    pajak = float(data.get('pajak', 0))
    total_akhir = float(data.get('total_akhir', 0))
    metode_pembayaran = data.get('metode_pembayaran', 'Tunai')
    bayar = float(data.get('bayar', 0))
    kembalian = float(data.get('kembalian', 0))
    catatan = data.get('catatan', '').strip()

    no_transaksi = get_next_trx_number()
    no_antrean = get_next_queue_number()
    total_item = sum(int(item['qty']) for item in items)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Simpan Transaksi Utama
            cursor.execute("""
                INSERT INTO transaksi 
                (no_transaksi, no_antrean, tanggal, member_id, nama_pelanggan, total_item, 
                 subtotal, diskon, pajak, total_akhir, metode_pembayaran, bayar, kembalian, 
                 status_antrean, catatan)
                VALUES (%s, %s, CURDATE(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Menunggu', %s)
            """, (
                no_transaksi, no_antrean, member_id, nama_pelanggan, total_item,
                subtotal, diskon, pajak, total_akhir, metode_pembayaran, bayar, kembalian, catatan
            ))
            transaksi_id = cursor.lastrowid

            # 2. Simpan Detail Transaksi
            for it in items:
                line_subtotal = float(it['harga']) * int(it['qty'])
                cursor.execute("""
                    INSERT INTO detail_transaksi (transaksi_id, menu_id, nama_menu, jumlah, harga_satuan, subtotal, catatan_item)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    transaksi_id, it['menu_id'], it['nama_menu'], it['qty'], it['harga'], line_subtotal, it.get('catatan_item', '')
                ))

            # 3. Update Poin Member jika transaksi tertaut member (1 poin per 10.000)
            if member_id:
                earned_points = int(total_akhir // 10000)
                if earned_points > 0:
                    cursor.execute("""
                        UPDATE pelanggan_member
                        SET poin = poin + %s
                        WHERE id = %s
                    """, (earned_points, member_id))

            conn.commit()

        # 4. Pengurangan Stok Bahan Baku Otomatis via Resep
        deduct_raw_materials_for_transaction(items, trx_no=no_transaksi)

        # 5. Log Aktivitas Admin
        log_activity(session['user_id'], session['username'], 'Transaksi Kasir POS', f"Transaksi {no_transaksi} ({no_antrean}) senilai Rp {total_akhir:,.0f}")

        # Return data lengkap untuk struk modal
        response_data = {
            'id': transaksi_id,
            'no_transaksi': no_transaksi,
            'no_antrean': no_antrean,
            'nama_pelanggan': nama_pelanggan,
            'subtotal': subtotal,
            'diskon': diskon,
            'total_akhir': total_akhir,
            'metode_pembayaran': metode_pembayaran,
            'bayar': bayar,
            'kembalian': kembalian,
            'created_at': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'items': items,
            'shop': g.shop
        }

        return jsonify({'status': 'success', 'data': response_data})

    except Exception as e:
        conn.rollback()
        print(f"[ERROR TRANSACTION] {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

# Struk Thermal View
@app.route('/transaksi/struk/<int:id>')
@login_required
def struk_print(id):
    trx = query_db("SELECT * FROM transaksi WHERE id = %s", (id,), one=True)
    if not trx:
        flash("Data transaksi tidak ditemukan.", "danger")
        return redirect(url_for('pos_page'))

    items = query_db("SELECT * FROM detail_transaksi WHERE transaksi_id = %s", (id,))
    return render_template('struk_print.html', trx=trx, items=items, shop=g.shop)

# Antrean Pesanan Board
@app.route('/antrean')
@login_required
def antrean_page():
    tgl = request.args.get('tanggal', datetime.date.today().isoformat())
    today_str = datetime.date.today().isoformat()

    all_q = query_db("""
        SELECT t.*, 
               GROUP_CONCAT(CONCAT(dt.nama_menu, ' x', dt.jumlah) SEPARATOR ', ') as items_summary
        FROM transaksi t
        LEFT JOIN detail_transaksi dt ON t.id = dt.transaksi_id
        WHERE t.tanggal = %s
        GROUP BY t.id
        ORDER BY t.id ASC
    """, (tgl,))

    menunggu = [q for q in all_q if q['status_antrean'] == 'Menunggu']
    diproses = [q for q in all_q if q['status_antrean'] == 'Diproses']
    selesai = [q for q in all_q if q['status_antrean'] == 'Selesai']
    dibatalkan = [q for q in all_q if q['status_antrean'] == 'Dibatalkan']

    return render_template(
        'antrean.html',
        active_page='antrean',
        antrean_menunggu=menunggu,
        antrean_diproses=diproses,
        antrean_selesai=selesai,
        antrean_dibatalkan=dibatalkan,
        selected_date=tgl,
        today_str=today_str
    )

@app.route('/antrean/update-status/<int:id>', methods=['POST'])
@login_required
def antrean_update_status(id):
    new_status = request.form.get('status')
    if new_status in ['Menunggu', 'Diproses', 'Selesai', 'Dibatalkan']:
        execute_db("UPDATE transaksi SET status_antrean = %s WHERE id = %s", (new_status, id))
        log_activity(session['user_id'], session['username'], 'Update Status Antrean', f"ID Transaksi {id} diubah status menjadi {new_status}")
        flash(f"Status antrean berhasil diubah menjadi: {new_status}", 'success')
    return redirect(url_for('antrean_page'))

# ========================================================
# 6. MANAJEMEN PELANGGAN / MEMBER
# ========================================================

@app.route('/member')
@login_required
def member_page():
    members = query_db("SELECT * FROM pelanggan_member ORDER BY id DESC")
    total_poin_res = query_db("SELECT SUM(poin) as total FROM pelanggan_member", one=True)
    total_poin = total_poin_res['total'] if total_poin_res and total_poin_res['total'] else 0

    next_num = len(members) + 1
    auto_kode_member = f"MBR-{next_num:03d}"

    return render_template(
        'member.html',
        active_page='member',
        members=members,
        total_poin=total_poin,
        auto_kode_member=auto_kode_member
    )

@app.route('/member/tambah', methods=['POST'])
@login_required
def member_tambah():
    kode_member = request.form.get('kode_member', '').strip().upper()
    nama = request.form.get('nama', '').strip()
    no_telp = request.form.get('no_telp', '').strip()
    email = request.form.get('email', '').strip()
    alamat = request.form.get('alamat', '').strip()
    poin = int(request.form.get('poin', 0))

    try:
        execute_db("""
            INSERT INTO pelanggan_member (kode_member, nama, no_telp, email, alamat, poin)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (kode_member, nama, no_telp, email, alamat, poin))
        log_activity(session['user_id'], session['username'], 'Tambah Member', f"Mendaftarkan member: {nama} ({kode_member})")
        flash(f"Member '{nama}' berhasil didaftarkan!", 'success')
    except Exception as e:
        flash(f"Gagal menambahkan member: {e}", 'danger')

    return redirect(url_for('member_page'))

@app.route('/member/edit/<int:id>', methods=['POST'])
@login_required
def member_edit(id):
    nama = request.form.get('nama', '').strip()
    no_telp = request.form.get('no_telp', '').strip()
    email = request.form.get('email', '').strip()
    alamat = request.form.get('alamat', '').strip()
    poin = int(request.form.get('poin', 0))

    execute_db("""
        UPDATE pelanggan_member
        SET nama=%s, no_telp=%s, email=%s, alamat=%s, poin=%s
        WHERE id=%s
    """, (nama, no_telp, email, alamat, poin, id))

    log_activity(session['user_id'], session['username'], 'Edit Member', f"Memperbarui member: {nama} (ID: {id})")
    flash(f"Data member '{nama}' berhasil diperbarui!", 'success')
    return redirect(url_for('member_page'))

@app.route('/member/hapus/<int:id>', methods=['POST'])
@login_required
def member_hapus(id):
    mem = query_db("SELECT nama FROM pelanggan_member WHERE id=%s", (id,), one=True)
    if mem:
        execute_db("DELETE FROM pelanggan_member WHERE id=%s", (id,))
        log_activity(session['user_id'], session['username'], 'Hapus Member', f"Menghapus member: {mem['nama']}")
        flash(f"Member '{mem['nama']}' berhasil dihapus.", 'info')
    return redirect(url_for('member_page'))

# ========================================================
# 7. LAPORAN PENJUALAN & EKSPOR
# ========================================================

@app.route('/laporan')
@login_required
def laporan_page():
    today = datetime.date.today()
    first_day_of_month = today.replace(day=1).isoformat()
    today_str = today.isoformat()

    tgl_awal = request.args.get('tgl_awal', first_day_of_month)
    tgl_akhir = request.args.get('tgl_akhir', today_str)
    selected_cat = request.args.get('kategori_id', '')

    # Query Transaksi
    sql = """
        SELECT t.*, pm.kode_member,
               GROUP_CONCAT(CONCAT(dt.nama_menu, ' (', dt.jumlah, ')') SEPARATOR ', ') as items_detail
        FROM transaksi t
        LEFT JOIN pelanggan_member pm ON t.member_id = pm.id
        LEFT JOIN detail_transaksi dt ON t.id = dt.transaksi_id
        LEFT JOIN menu_item mi ON dt.menu_id = mi.id
        WHERE t.tanggal BETWEEN %s AND %s AND t.status_antrean != 'Dibatalkan'
    """
    params = [tgl_awal, tgl_akhir]

    if selected_cat:
        sql += " AND mi.kategori_id = %s"
        params.append(selected_cat)

    sql += " GROUP BY t.id ORDER BY t.id DESC"
    transactions = query_db(sql, params)

    # Ringkasan KPI
    total_omset = sum(float(t['total_akhir']) for t in transactions) if transactions else 0
    total_trx = len(transactions)
    total_porsi = sum(int(t['total_item']) for t in transactions) if transactions else 0
    avg_trx = (total_omset / total_trx) if total_trx > 0 else 0

    # Best Seller Periode Ini
    best_sellers = query_db("""
        SELECT mi.nama_menu, k.nama_kategori,
               SUM(dt.jumlah) as total_terjual,
               SUM(dt.subtotal) as total_omset
        FROM detail_transaksi dt
        JOIN transaksi t ON dt.transaksi_id = t.id
        JOIN menu_item mi ON dt.menu_id = mi.id
        JOIN kategori k ON mi.kategori_id = k.id
        WHERE t.tanggal BETWEEN %s AND %s AND t.status_antrean != 'Dibatalkan'
        GROUP BY dt.menu_id, mi.nama_menu, k.nama_kategori
        ORDER BY total_terjual DESC
        LIMIT 5
    """, (tgl_awal, tgl_akhir))

    # Ringkasan Mutasi Bahan
    stock_summary = query_db("""
        SELECT b.nama_bahan, b.satuan, b.stok, b.stok_minimal,
               SUM(CASE WHEN l.jenis = 'Masuk' THEN l.jumlah ELSE 0 END) as total_masuk,
               SUM(CASE WHEN l.jenis = 'Keluar' THEN l.jumlah ELSE 0 END) as total_keluar
        FROM bahan_baku b
        LEFT JOIN log_stok_bahan l ON b.id = l.bahan_id AND DATE(l.created_at) BETWEEN %s AND %s
        GROUP BY b.id
        ORDER BY b.stok ASC
        LIMIT 6
    """, (tgl_awal, tgl_akhir))

    categories = query_db("SELECT id, nama_kategori FROM kategori ORDER BY id ASC")

    return render_template(
        'laporan.html',
        active_page='laporan',
        transactions=transactions,
        total_omset=total_omset,
        total_transaksi_count=total_trx,
        total_porsi=total_porsi,
        avg_transaksi=avg_trx,
        best_sellers=best_sellers,
        stock_summary=stock_summary,
        categories=categories,
        tgl_awal=tgl_awal,
        tgl_akhir=tgl_akhir,
        selected_cat=selected_cat
    )

@app.route('/laporan/export-excel')
@login_required
def laporan_export_excel():
    today = datetime.date.today()
    tgl_awal = request.args.get('tgl_awal', today.replace(day=1).isoformat())
    tgl_akhir = request.args.get('tgl_akhir', today.isoformat())

    sql = """
        SELECT t.no_transaksi, t.tanggal, t.nama_pelanggan, t.total_item, 
               t.subtotal, t.diskon, t.total_akhir, t.metode_pembayaran, t.status_antrean,
               GROUP_CONCAT(CONCAT(dt.nama_menu, ' x', dt.jumlah) SEPARATOR '; ') as rincian_menu
        FROM transaksi t
        LEFT JOIN detail_transaksi dt ON t.id = dt.transaksi_id
        WHERE t.tanggal BETWEEN %s AND %s AND t.status_antrean != 'Dibatalkan'
        GROUP BY t.id
        ORDER BY t.id ASC
    """
    transactions = query_db(sql, (tgl_awal, tgl_akhir))

    # Buat Workbook Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Laporan Penjualan"

    # Styling
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=16, bold=True, color="0284C7")
    subtitle_font = Font(name="Calibri", size=11, bold=False, color="64748B")
    border_thin = Border(left=Side(style='thin', color='E2E8F0'),
                         right=Side(style='thin', color='E2E8F0'),
                         top=Side(style='thin', color='E2E8F0'),
                         bottom=Side(style='thin', color='E2E8F0'))

    # Title Banner
    ws.merge_cells('A1:I1')
    ws['A1'] = f"{g.shop.get('nama_toko', 'Kedai Es Teler Juara 77')} - Laporan Penjualan"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

    ws.merge_cells('A2:I2')
    ws['A2'] = f"Periode: {tgl_awal} s/d {tgl_akhir} | Dicetak: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')

    # Table Header
    headers = ["No", "No. Transaksi", "Tanggal", "Pelanggan", "Menu Dipesan", "Subtotal (Rp)", "Diskon (Rp)", "Total Akhir (Rp)", "Metode"]
    ws.append([]) # row 3 empty
    ws.append(headers) # row 4

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=4, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Data Rows
    row_num = 5
    total_omset = 0
    for idx, t in enumerate(transactions, 1):
        ws.append([
            idx,
            t['no_transaksi'],
            str(t['tanggal']),
            t['nama_pelanggan'],
            t['rincian_menu'] or '-',
            float(t['subtotal']),
            float(t['diskon']),
            float(t['total_akhir']),
            t['metode_pembayaran']
        ])
        total_omset += float(t['total_akhir'])
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.border = border_thin
            if col_idx in [6, 7, 8]:
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal='right')
        row_num += 1

    # Total Row
    ws.append(["", "", "", "", "TOTAL OMSET PENJUALAN", "", "", total_omset, ""])
    ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=5)
    total_label = ws.cell(row=row_num, column=1)
    total_label.font = Font(name="Calibri", size=11, bold=True)
    total_label.alignment = Alignment(horizontal='right')
    total_val = ws.cell(row=row_num, column=8)
    total_val.font = Font(name="Calibri", size=11, bold=True, color="0284C7")
    total_val.number_format = '#,##0'

    # Auto-adjust column width
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Laporan_Penjualan_EsTeler_{tgl_awal}_{tgl_akhir}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/laporan/export-pdf')
@login_required
def laporan_export_pdf():
    today = datetime.date.today()
    tgl_awal = request.args.get('tgl_awal', today.replace(day=1).isoformat())
    tgl_akhir = request.args.get('tgl_akhir', today.isoformat())

    sql = """
        SELECT t.no_transaksi, t.tanggal, t.nama_pelanggan, 
               t.total_item, t.total_akhir, t.metode_pembayaran
        FROM transaksi t
        WHERE t.tanggal BETWEEN %s AND %s AND t.status_antrean != 'Dibatalkan'
        ORDER BY t.id ASC
    """
    transactions = query_db(sql, (tgl_awal, tgl_akhir))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#0284C7'), alignment=1, spaceAfter=4)
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#64748B'), alignment=1, spaceAfter=15)

    story.append(Paragraph(f"<b>{g.shop.get('nama_toko', 'Kedai Es Teler Juara 77')}</b>", title_style))
    story.append(Paragraph(f"Laporan Rekapitulasi Penjualan &bull; Periode: {tgl_awal} s/d {tgl_akhir}", subtitle_style))

    # Table data
    data = [["No", "No. Transaksi", "Tanggal", "Pelanggan", "Porsi", "Total (Rp)", "Metode"]]
    total_omset = 0
    for idx, t in enumerate(transactions, 1):
        total_omset += float(t['total_akhir'])
        data.append([
            str(idx),
            t['no_transaksi'],
            str(t['tanggal']),
            t['nama_pelanggan'],
            str(t['total_item']),
            f"Rp {t['total_akhir']:,.0f}".replace(',', '.'),
            t['metode_pembayaran']
        ])

    data.append(["", "", "", "TOTAL OMSET", "", f"Rp {total_omset:,.0f}".replace(',', '.'), ""])

    table = Table(data, colWidths=[30, 95, 70, 130, 45, 95, 65])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284C7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'LEFT'),
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8FAFC')]),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#0284C7')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 9.5),
        ('TEXTCOLOR', (5, -1), (5, -1), colors.HexColor('#0284C7')),
    ]))

    story.append(table)
    doc.build(story)
    buffer.seek(0)

    filename = f"Laporan_Penjualan_EsTeler_{tgl_awal}_{tgl_akhir}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")

# ========================================================
# 8. PENGATURAN, LOG AKTIVITAS & BACKUP DATABASE
# ========================================================

@app.route('/log-aktivitas')
@login_required
def log_aktivitas_page():
    logs = query_db("SELECT * FROM log_aktivitas ORDER BY id DESC LIMIT 100")
    return render_template('log_aktivitas.html', active_page='log', logs=logs)

@app.route('/pengaturan')
@login_required
def pengaturan_page():
    admin_user = query_db("SELECT id, username, email, nama_lengkap FROM users WHERE id = %s", (session['user_id'],), one=True)
    return render_template(
        'pengaturan.html',
        active_page='pengaturan',
        shop=g.shop,
        admin_user=admin_user
    )

@app.route('/pengaturan/simpan', methods=['POST'])
@login_required
def pengaturan_simpan():
    nama_toko = request.form.get('nama_toko', '').strip()
    slogan = request.form.get('slogan', '').strip()
    no_telepon = request.form.get('no_telepon', '').strip()
    email = request.form.get('email', '').strip()
    alamat = request.form.get('alamat', '').strip()
    pesan_struk_header = request.form.get('pesan_struk_header', '').strip()
    pesan_struk_footer = request.form.get('pesan_struk_footer', '').strip()

    execute_db("""
        UPDATE pengaturan
        SET nama_toko=%s, slogan=%s, no_telepon=%s, email=%s, alamat=%s, 
            pesan_struk_header=%s, pesan_struk_footer=%s
        WHERE id=1
    """, (nama_toko, slogan, no_telepon, email, alamat, pesan_struk_header, pesan_struk_footer))

    log_activity(session['user_id'], session['username'], 'Pengaturan Kedai', 'Memperbarui profil kedai dan format struk')
    flash('Pengaturan kedai berhasil disimpan!', 'success')
    return redirect(url_for('pengaturan_page'))

@app.route('/pengaturan/admin', methods=['POST'])
@login_required
def pengaturan_admin():
    nama_lengkap = request.form.get('nama_lengkap', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password_baru = request.form.get('password_baru', '').strip()

    if password_baru:
        hashed = generate_password_hash(password_baru)
        execute_db("""
            UPDATE users
            SET nama_lengkap=%s, username=%s, email=%s, password=%s
            WHERE id=%s
        """, (nama_lengkap, username, email, hashed, session['user_id']))
    else:
        execute_db("""
            UPDATE users
            SET nama_lengkap=%s, username=%s, email=%s
            WHERE id=%s
        """, (nama_lengkap, username, email, session['user_id']))

    session['username'] = username
    session['user_nama'] = nama_lengkap

    log_activity(session['user_id'], username, 'Update Akun Admin', 'Memperbarui kredensial akun admin')
    flash('Akun admin berhasil diperbarui!', 'success')
    return redirect(url_for('pengaturan_page'))

@app.route('/database/backup')
@login_required
def database_backup():
    """Menghasilkan file export .sql dump langsung dari database."""
    tables = ['pengaturan', 'users', 'kategori', 'bahan_baku', 'menu_item', 'menu_resep', 'log_stok_bahan', 'pelanggan_member', 'transaksi', 'detail_transaksi', 'log_aktivitas']
    sql_dump = []
    sql_dump.append(f"-- BACKUP DATABASE KEDAI ES TELER JUARA 77")
    sql_dump.append(f"-- Waktu Backup: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_dump.append(f"-- Generated by Admin: {session.get('username')}\n")
    sql_dump.append("SET FOREIGN_KEY_CHECKS = 0;\n")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for tbl in tables:
                cursor.execute(f"SHOW CREATE TABLE `{tbl}`")
                create_res = cursor.fetchone()
                if create_res:
                    sql_dump.append(f"DROP TABLE IF EXISTS `{tbl}`;")
                    sql_dump.append(create_res['Create Table'] + ";\n")

                cursor.execute(f"SELECT * FROM `{tbl}`")
                rows = cursor.fetchall()
                if rows:
                    cols = ", ".join([f"`{k}`" for k in rows[0].keys()])
                    for r in rows:
                        vals = []
                        for v in r.values():
                            if v is None:
                                vals.append("NULL")
                            elif isinstance(v, (int, float)):
                                vals.append(str(v))
                            else:
                                clean_val = str(v).replace("\\", "\\\\").replace("'", "\\'")
                                vals.append(f"'{clean_val}'")
                        val_str = ", ".join(vals)
                        sql_dump.append(f"INSERT INTO `{tbl}` ({cols}) VALUES ({val_str});")
                    sql_dump.append("")
        sql_dump.append("SET FOREIGN_KEY_CHECKS = 1;")
    finally:
        conn.close()

    full_sql = "\n".join(sql_dump)
    filename = f"backup_esteler_{datetime.date.today().strftime('%Y%m%d')}.sql"
    return Response(full_sql, mimetype="application/sql", headers={"Content-Disposition": f"attachment;filename={filename}"})

@app.route('/database/restore', methods=['POST'])
@login_required
def database_restore():
    file = request.files.get('backup_file')
    if not file or file.filename == '':
        flash("Silakan pilih file backup .sql", "danger")
        return redirect(url_for('pengaturan_page'))

    try:
        sql_content = file.read().decode('utf-8')
        queries = sql_content.split(';')
        conn = get_db_connection()
        with conn.cursor() as cursor:
            for q in queries:
                cleaned = q.strip()
                if cleaned:
                    cursor.execute(cleaned)
            conn.commit()
        conn.close()
        log_activity(session['user_id'], session['username'], 'Restore Database', f"Memulihkan database dari {file.filename}")
        flash("Database berhasil dipulihkan dari file backup!", "success")
    except Exception as e:
        flash(f"Gagal memulihkan database: {e}", "danger")

    return redirect(url_for('pengaturan_page'))

# ========================================================
# RUN APPLICATION
# ========================================================
if __name__ == '__main__':
    port = Config.PORT
    debug = Config.DEBUG
    print("=" * 55)
    print(" SISTEM INFORMASI PENJUALAN ES TELER (FLASK & MYSQL)  ")
    print(f" Berjalan di: http://localhost:{port}/es_teler_pos/member")
    print(" Akun Admin Default: admin / admin123                 ")
    print("=" * 55)
    app.run(host='0.0.0.0', port=port, debug=debug)