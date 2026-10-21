-- ========================================================
-- SISTEM INFORMASI PENJUALAN ES TELER (POS & OPERASIONAL)
-- Database: db_penjualan_esteler
-- ========================================================

CREATE DATABASE IF NOT EXISTS `db_penjualan_esteler` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `db_penjualan_esteler`;

-- 1. TABEL PENGATURAN KEDAI / TOKO
CREATE TABLE IF NOT EXISTS `pengaturan` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nama_toko` VARCHAR(150) NOT NULL DEFAULT 'Kedai Es Teler Juara 77',
    `slogan` VARCHAR(255) DEFAULT 'Sensasi Kesegaran Asli Buah Nusantara',
    `alamat` TEXT,
    `no_telepon` VARCHAR(50) DEFAULT '0812-3456-7890',
    `email` VARCHAR(100) DEFAULT 'estelerjuara77@gmail.com',
    `pesan_struk_header` TEXT,
    `pesan_struk_footer` TEXT,
    `logo` VARCHAR(255) DEFAULT 'logo.png',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. TABEL USERS (AKUN ADMIN)
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `nama_lengkap` VARCHAR(100) NOT NULL,
    `role` VARCHAR(20) NOT NULL DEFAULT 'admin',
    `foto` VARCHAR(255) DEFAULT 'default_admin.png',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. TABEL KATEGORI
CREATE TABLE IF NOT EXISTS `kategori` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nama_kategori` VARCHAR(100) NOT NULL,
    `deskripsi` TEXT,
    `icon` VARCHAR(50) DEFAULT 'bi-cup-straw',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. TABEL BAHAN BAKU
CREATE TABLE IF NOT EXISTS `bahan_baku` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nama_bahan` VARCHAR(120) NOT NULL,
    `satuan` VARCHAR(50) NOT NULL,
    `stok` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `stok_minimal` DECIMAL(10,2) NOT NULL DEFAULT 5.00,
    `harga_satuan` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. TABEL MENU ITEM
CREATE TABLE IF NOT EXISTS `menu_item` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `kategori_id` INT NOT NULL,
    `kode_menu` VARCHAR(30) NOT NULL UNIQUE,
    `nama_menu` VARCHAR(150) NOT NULL,
    `deskripsi` TEXT,
    `harga` DECIMAL(12,2) NOT NULL,
    `status` ENUM('Tersedia', 'Habis') NOT NULL DEFAULT 'Tersedia',
    `gambar` VARCHAR(255) DEFAULT 'default_menu.jpg',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`kategori_id`) REFERENCES `kategori`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. TABEL MENU RESEP (KOMPOSISI BAHAN BAKU UNTUK PENGURANGAN STOK OTOMATIS)
CREATE TABLE IF NOT EXISTS `menu_resep` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `menu_id` INT NOT NULL,
    `bahan_id` INT NOT NULL,
    `jumlah_pakai` DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (`menu_id`) REFERENCES `menu_item`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`bahan_id`) REFERENCES `bahan_baku`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. TABEL LOG STOK BAHAN BAKU (MUTASI STOK MASUK / KELUAR)
CREATE TABLE IF NOT EXISTS `log_stok_bahan` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `bahan_id` INT NOT NULL,
    `jenis` ENUM('Masuk', 'Keluar') NOT NULL,
    `jumlah` DECIMAL(10,2) NOT NULL,
    `stok_sebelum` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `stok_sesudah` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `keterangan` VARCHAR(255),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`bahan_id`) REFERENCES `bahan_baku`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. TABEL PELANGGAN / MEMBER
CREATE TABLE IF NOT EXISTS `pelanggan_member` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `kode_member` VARCHAR(30) NOT NULL UNIQUE,
    `nama` VARCHAR(100) NOT NULL,
    `no_telp` VARCHAR(25) NOT NULL,
    `email` VARCHAR(100),
    `alamat` TEXT,
    `poin` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. TABEL TRANSAKSI PENJUALAN
CREATE TABLE IF NOT EXISTS `transaksi` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `no_transaksi` VARCHAR(50) NOT NULL UNIQUE,
    `no_antrean` VARCHAR(20) NOT NULL,
    `tanggal` DATE NOT NULL,
    `member_id` INT NULL,
    `nama_pelanggan` VARCHAR(100) DEFAULT 'Pelanggan Umum',
    `total_item` INT NOT NULL DEFAULT 1,
    `subtotal` DECIMAL(12,2) NOT NULL,
    `diskon` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    `pajak` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    `total_akhir` DECIMAL(12,2) NOT NULL,
    `metode_pembayaran` ENUM('Tunai', 'QRIS', 'Transfer', 'Debit') NOT NULL DEFAULT 'Tunai',
    `bayar` DECIMAL(12,2) NOT NULL,
    `kembalian` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    `status_antrean` ENUM('Menunggu', 'Diproses', 'Selesai', 'Dibatalkan') NOT NULL DEFAULT 'Menunggu',
    `catatan` TEXT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `pelanggan_member`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. TABEL DETAIL TRANSAKSI
CREATE TABLE IF NOT EXISTS `detail_transaksi` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `transaksi_id` INT NOT NULL,
    `menu_id` INT NULL,
    `nama_menu` VARCHAR(150) NOT NULL,
    `jumlah` INT NOT NULL DEFAULT 1,
    `harga_satuan` DECIMAL(12,2) NOT NULL,
    `subtotal` DECIMAL(12,2) NOT NULL,
    `catatan_item` VARCHAR(255),
    FOREIGN KEY (`transaksi_id`) REFERENCES `transaksi`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`menu_id`) REFERENCES `menu_item`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. TABEL LOG AKTIVITAS ADMIN
CREATE TABLE IF NOT EXISTS `log_aktivitas` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `username` VARCHAR(50),
    `aktivitas` VARCHAR(100) NOT NULL,
    `detail` TEXT,
    `ip_address` VARCHAR(45),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================================
-- DATA DUMMY / SIMULASI AWAL (SEED DATA)
-- ========================================================

-- Seed Pengaturan
INSERT INTO `pengaturan` (`id`, `nama_toko`, `slogan`, `alamat`, `no_telepon`, `email`, `pesan_struk_header`, `pesan_struk_footer`, `logo`)
VALUES (1, 'Kedai Es Teler Juara 77', 'Sensasi Kesegaran Asli Buah Nusantara', 'Jl. Boulevard Hijau No. 77, Jakarta', '0812-3456-7890', 'estelerjuara77@gmail.com', 'Selamat Datang di Kedai Es Teler Juara 77!\nNikmati Kesegaran Buah Pilihan Terbaik', 'Terima Kasih atas Kunjungan Anda!\nFollow Instagram kami: @estelerjuara77\nKritik & Saran WA: 0812-3456-7890', 'logo.png')
ON DUPLICATE KEY UPDATE `nama_toko`=VALUES(`nama_toko`);

-- Seed Users (Admin: admin / admin123)
INSERT INTO `users` (`id`, `username`, `email`, `password`, `nama_lengkap`, `role`)
VALUES (1, 'admin', 'admin@estelerjuara.com', 'scrypt:32768:8:1$domCeoRxMjdyUoRc$571e9d19ce4a52d0e79fcde2f16b8b4b0c58e5bbc8e885232dc532db85e99146ee7a9dadd5add07caa6420df494108ad0aaae1e7a23746b61d29f85489921fb4', 'Administrator Kedai', 'admin')
ON DUPLICATE KEY UPDATE `username`=VALUES(`username`);

-- Seed Kategori
INSERT INTO `kategori` (`id`, `nama_kategori`, `deskripsi`, `icon`) VALUES
(1, 'Spesial Es Teler', 'Varian Es Teler istimewa racikan khas nusantara dengan buah segar pilihan', 'bi-stars'),
(2, 'Aneka Es Tradisional', 'Minuman es tradisional Indonesia pelepas dahaga yang otentik', 'bi-cup-straw'),
(3, 'Jus & Minuman Segar', 'Jus buah murni dan minuman dingin pelega tenggorokan', 'bi-water'),
(4, 'Camilan Pendamping', 'Kudapan gurih & manis pelengkap menikmati sajian es', 'bi-cookie')
ON DUPLICATE KEY UPDATE `nama_kategori`=VALUES(`nama_kategori`);

-- Seed Bahan Baku
INSERT INTO `bahan_baku` (`id`, `nama_bahan`, `satuan`, `stok`, `stok_minimal`, `harga_satuan`) VALUES
(1, 'Alpukat Mentega Segar', 'Kg', 18.50, 5.00, 25000.00),
(2, 'Daging Kelapa Muda', 'Kg', 22.00, 5.00, 20000.00),
(3, 'Nangka Manis Matang', 'Kg', 9.00, 3.00, 28000.00),
(4, 'Daging Durian Montong', 'Kg', 2.50, 4.00, 85000.00), -- Di bawah stok minimal (Alert!)
(5, 'Susu Kental Manis', 'Kaleng', 32.00, 10.00, 12500.00),
(6, 'Sirup Gula Rahasia Juara', 'Liter', 15.00, 5.00, 15000.00),
(7, 'Santan Kelapa Matang', 'Liter', 3.00, 5.00, 18000.00), -- Di bawah stok minimal (Alert!)
(8, 'Es Batu Kristal Higienis', 'Kg', 60.00, 20.00, 2000.00),
(9, 'Cup & Tutup Plastik 16oz', 'Pcs', 180.00, 50.00, 500.00),
(10, 'Mangkok Melamin Saji', 'Pcs', 45.00, 20.00, 15000.00),
(11, 'Sedotan & Sendok Bebek', 'Pcs', 250.00, 50.00, 150.00),
(12, 'Keju Cheddar Parut', 'Balok', 5.00, 2.00, 22000.00),
(13, 'Biji Selasih Organik', 'Gram', 600.00, 200.00, 60.00),
(14, 'Cincau Hitam Alami', 'Kg', 10.00, 3.00, 14000.00)
ON DUPLICATE KEY UPDATE `nama_bahan`=VALUES(`nama_bahan`);

-- Seed Log Stok Awal (Mutasi)
INSERT INTO `log_stok_bahan` (`bahan_id`, `jenis`, `jumlah`, `stok_sebelum`, `stok_sesudah`, `keterangan`) VALUES
(1, 'Masuk', 20.00, 0.00, 20.00, 'Stok awal pasokan buah pasar induk'),
(2, 'Masuk', 25.00, 0.00, 25.00, 'Stok awal kelapa muda dari petani'),
(3, 'Masuk', 10.00, 0.00, 10.00, 'Stok awal nangka manis'),
(4, 'Masuk', 5.00, 0.00, 5.00, 'Pengadaan durian montong beku'),
(4, 'Keluar', 2.50, 5.00, 2.50, 'Pemakaian batch produksi pagi'),
(7, 'Keluar', 2.00, 5.00, 3.00, 'Pemakaian santan kelapa');

-- Seed Menu Items
INSERT INTO `menu_item` (`id`, `kategori_id`, `kode_menu`, `nama_menu`, `deskripsi`, `harga`, `status`, `gambar`) VALUES
(1, 1, 'MN-001', 'Es Teler Original Juara', 'Perpaduan legendaris alpukat mentega, kelapa muda, nangka manis, disiram santan gurih, susu kental manis dan sirup rahasia juara.', 18000.00, 'Tersedia', 'es_teler_original.jpg'),
(2, 1, 'MN-002', 'Es Teler Durian Sultan', 'Es Teler original juara dengan topping daging durian montong premium yang lumer, legit dan harum semerbak.', 28000.00, 'Tersedia', 'es_teler_durian.jpg'),
(3, 1, 'MN-003', 'Es Teler Keju Melimpah', 'Sajian Es Teler nikmat dengan limpahan parutan keju cheddar gurih tebal yang berpadu sempurna dengan manisnya buah.', 22000.00, 'Tersedia', 'es_teler_keju.jpg'),
(4, 1, 'MN-004', 'Es Teler Alpukat Kocok', 'Alpukat mentega pilihan yang dikocok kental berpadu dengan kelapa muda, nangka, dan susu cokelat/putih.', 22000.00, 'Tersedia', 'es_teler_alpukat_kocok.jpg'),
(5, 2, 'MN-005', 'Es Kelapa Muda Jeruk', 'Daging kelapa muda lembut berpadu dengan perasan jeruk peras asli yang kaya vitamin C dan super segar.', 15000.00, 'Tersedia', 'es_kelapa_jeruk.jpg'),
(6, 2, 'MN-006', 'Es Cincau Susu Gula Aren', 'Cincau hitam kenyal lembut dipadu dengan susu segar dan harum legitnya gula aren murni.', 13000.00, 'Tersedia', 'es_cincau_aren.jpg'),
(7, 2, 'MN-007', 'Es Kuwut Bali Segar', 'Minuman segar khas Bali dengan serutan melon, kelapa muda, air jeruk nipis, dan biji selasih.', 14000.00, 'Tersedia', 'es_kuwut_bali.jpg'),
(8, 2, 'MN-008', 'Es Campur Segar Manis', 'Kombinasi tape singkong, kolang-kaling warna-warni, cincau, nangka dan roti tawar dengan sirup mawar.', 16000.00, 'Tersedia', 'es_campur.jpg'),
(9, 3, 'MN-009', 'Jus Alpukat Mentega', 'Jus buah alpukat mentega kental disajikan dengan lelehan susu kental manis cokelat.', 16000.00, 'Tersedia', 'jus_alpukat.jpg'),
(10, 3, 'MN-010', 'Es Lemon Tea Mint', 'Teh segar dipadukan dengan irisan lemon asli dan daun mint segar penyejuk tenggorokan.', 10000.00, 'Tersedia', 'es_lemon_tea.jpg'),
(11, 4, 'MN-011', 'Pisang Goreng Crispy Keju', 'Pisang kepok manis digoreng tepung crispy renyah dengan taburan keju cheddar dan susu manis.', 15000.00, 'Tersedia', 'pisang_crispy.jpg'),
(12, 4, 'MN-012', 'Roti Bakar Cokelat Keju', 'Roti tebal dipanggang renyah dengan isian meses cokelat premium dan keju gurih melimpah.', 16000.00, 'Tersedia', 'roti_bakar.jpg'),
(13, 4, 'MN-013', 'Cireng Krispy Bumbu Rujak', 'Cireng kenyal gurih di luar empuk di dalam dicocol dengan saus bumbu rujak pedas manis asam.', 12000.00, 'Tersedia', 'cireng_rujak.jpg'),
(14, 4, 'MN-014', 'Kentang Goreng Saus Keju', 'Kentang goreng renyah disajikan dengan saus keju creamy istimewa.', 14000.00, 'Tersedia', 'kentang_keju.jpg')
ON DUPLICATE KEY UPDATE `nama_menu`=VALUES(`nama_menu`);

-- Seed Resep Bahan Baku (Menu -> Bahan Baku untuk Auto Pengurangan Stok)
INSERT INTO `menu_resep` (`menu_id`, `bahan_id`, `jumlah_pakai`) VALUES
-- Es Teler Original (ID: 1)
(1, 1, 0.10), -- 0.1 Kg Alpukat
(1, 2, 0.10), -- 0.1 Kg Kelapa
(1, 3, 0.05), -- 0.05 Kg Nangka
(1, 5, 0.10), -- 0.1 Kaleng Susu
(1, 6, 0.05), -- 0.05 L Sirup
(1, 7, 0.05), -- 0.05 L Santan
(1, 8, 0.25), -- 0.25 Kg Es Batu
(1, 9, 1.00), -- 1 Cup
(1, 11, 1.00),-- 1 Sendok/Sedotan
-- Es Teler Durian Sultan (ID: 2)
(2, 4, 0.10), -- 0.1 Kg Durian
(2, 1, 0.08), -- Alpukat
(2, 2, 0.08), -- Kelapa
(2, 5, 0.10), -- Susu
(2, 8, 0.25), -- Es batu
(2, 9, 1.00), -- Cup
(2, 11, 1.00),-- Sendok
-- Es Teler Keju (ID: 3)
(3, 1, 0.10),
(3, 2, 0.10),
(3, 3, 0.05),
(3, 12, 0.15), -- 0.15 Balok Keju
(3, 5, 0.10),
(3, 9, 1.00),
-- Es Kelapa Muda Jeruk (ID: 5)
(5, 2, 0.15),
(5, 8, 0.25),
(5, 9, 1.00),
(5, 11, 1.00);

-- Seed Pelanggan / Member
INSERT INTO `pelanggan_member` (`id`, `kode_member`, `nama`, `no_telp`, `email`, `alamat`, `poin`) VALUES
(1, 'MBR-001', 'Budi Santoso', '081234567890', 'budi.santoso@gmail.com', 'Jl. Merdeka No. 12, Jakarta', 120),
(2, 'MBR-002', 'Siti Rahmawati', '081398765432', 'siti.rahma@yahoo.com', 'Jl. Kebon Jeruk No. 45, Jakarta', 85),
(3, 'MBR-003', 'Rizky Pratama', '085711223344', 'rizky.pratama@gmail.com', 'Jl. Sudirman Kav 20, Jakarta', 45),
(4, 'MBR-004', 'Dewi Lestari', '087855667788', 'dewi.lestari@gmail.com', 'Jl. Melati Indah Blok C3, Jakarta', 90)
ON DUPLICATE KEY UPDATE `nama`=VALUES(`nama`);

-- Seed Transaksi Simulasi Hari Ini & Kemarin
INSERT INTO `transaksi` (`id`, `no_transaksi`, `no_antrean`, `tanggal`, `member_id`, `nama_pelanggan`, `total_item`, `subtotal`, `diskon`, `pajak`, `total_akhir`, `metode_pembayaran`, `bayar`, `kembalian`, `status_antrean`, `catatan`, `created_at`) VALUES
(1, 'TRX-20261020-001', 'A-001', CURDATE(), 1, 'Budi Santoso', 3, 64000.00, 0.00, 0.00, 64000.00, 'QRIS', 64000.00, 0.00, 'Selesai', 'Es teler dipisah es batunya', DATE_SUB(NOW(), INTERVAL 3 HOUR)),
(2, 'TRX-20261020-002', 'A-002', CURDATE(), NULL, 'Pelanggan Umum', 2, 36000.00, 0.00, 0.00, 36000.00, 'Tunai', 50000.00, 14000.00, 'Selesai', 'Makan di tempat meja 4', DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(3, 'TRX-20261020-003', 'A-003', CURDATE(), 2, 'Siti Rahmawati', 4, 76000.00, 5000.00, 0.00, 71000.00, 'Tunai', 100000.00, 29000.00, 'Diproses', 'Bungkus rapi untuk kantor', DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(4, 'TRX-20261020-004', 'A-004', CURDATE(), NULL, 'Andi Wijaya', 2, 46000.00, 0.00, 0.00, 46000.00, 'Transfer', 46000.00, 0.00, 'Menunggu', 'Tolong jangan terlalu manis', DATE_SUB(NOW(), INTERVAL 15 MINUTE));

-- Detail Transaksi
INSERT INTO `detail_transaksi` (`transaksi_id`, `menu_id`, `nama_menu`, `jumlah`, `harga_satuan`, `subtotal`, `catatan_item`) VALUES
(1, 1, 'Es Teler Original Juara', 2, 18000.00, 36000.00, 'Manis sedang'),
(1, 2, 'Es Teler Durian Sultan', 1, 28000.00, 28000.00, 'Extra durian'),
(2, 1, 'Es Teler Original Juara', 2, 18000.00, 36000.00, NULL),
(3, 1, 'Es Teler Original Juara', 2, 18000.00, 36000.00, NULL),
(3, 3, 'Es Teler Keju Melimpah', 1, 22000.00, 22000.00, NULL),
(3, 11, 'Pisang Goreng Crispy Keju', 1, 15000.00, 15000.00, 'Hangat'),
(4, 2, 'Es Teler Durian Sultan', 1, 28000.00, 28000.00, NULL),
(4, 1, 'Es Teler Original Juara', 1, 18000.00, 18000.00, NULL);

-- Seed Log Aktivitas
INSERT INTO `log_aktivitas` (`user_id`, `username`, `aktivitas`, `detail`, `ip_address`, `created_at`) VALUES
(1, 'admin', 'Login Admin', 'Admin berhasil login ke sistem', '127.0.0.1', DATE_SUB(NOW(), INTERVAL 4 HOUR)),
(1, 'admin', 'Transaksi Kasir POS', 'Membuat transaksi baru TRX-20261020-001 senilai Rp 64.000', '127.0.0.1', DATE_SUB(NOW(), INTERVAL 3 HOUR)),
(1, 'admin', 'Transaksi Kasir POS', 'Membuat transaksi baru TRX-20261020-002 senilai Rp 36.000', '127.0.0.1', DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(1, 'admin', 'Update Antrean', 'Mengubah status antrean A-001 menjadi Selesai', '127.0.0.1', DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(1, 'admin', 'Transaksi Kasir POS', 'Membuat transaksi baru TRX-20261020-003 senilai Rp 71.000', '127.0.0.1', DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(1, 'admin', 'Transaksi Kasir POS', 'Membuat transaksi baru TRX-20261020-004 senilai Rp 46.000', '127.0.0.1', DATE_SUB(NOW(), INTERVAL 15 MINUTE));
