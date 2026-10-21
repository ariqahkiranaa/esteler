<?php
// Redirect otomatis ke port 5000 (Server Python Flask)
header("Location: http://localhost:5000/");
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=http://localhost:5000/">
    <title>Membuka Sistem Penjualan Es Teler...</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #F8FAFC;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            color: #0F172A;
        }
        .card {
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
            text-align: center;
            max-width: 450px;
        }
        .btn {
            display: inline-block;
            background: #0284C7;
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: bold;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>🍧 Kedai Es Teler Juara 77</h2>
        <p>Aplikasi ini berbasis <strong>Python Flask</strong> dan berjalan di port 5000.</p>
        <p>Sedang mengalihkan ke aplikasi...</p>
        <a href="http://localhost:5000/" class="btn">Klik Di Sini untuk Membuka Aplikasi</a>
    </div>
    <script>
        window.location.href = "http://localhost:5000/";
    </script>
</body>
</html>
