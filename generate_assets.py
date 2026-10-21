import os

img_dir = os.path.join(os.path.dirname(__file__), "static", "img")
uploads_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(img_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)

# 1. Logo SVG
logo_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100" width="100%" height="100%">
  <defs>
    <linearGradient id="gradBrand" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284C7" />
      <stop offset="100%" stop-color="#10B981" />
    </linearGradient>
    <linearGradient id="gradBowl" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38BDF8" />
      <stop offset="100%" stop-color="#0284C7" />
    </linearGradient>
  </defs>
  <!-- Bowl Icon -->
  <g transform="translate(10, 10)">
    <circle cx="40" cy="40" r="38" fill="url(#gradBrand)" opacity="0.15"/>
    <!-- Fresh Ice & Fruits in Bowl -->
    <path d="M 20 40 Q 40 25 60 40" fill="none" stroke="#FBBF24" stroke-width="4" stroke-linecap="round"/>
    <path d="M 28 32 Q 40 20 52 32" fill="none" stroke="#10B981" stroke-width="3" stroke-linecap="round"/>
    <!-- Coconut / Avocado slice -->
    <circle cx="34" cy="34" r="7" fill="#84CC16" />
    <circle cx="48" cy="32" r="6" fill="#F59E0B" />
    <!-- Bowl body -->
    <path d="M 16 42 Q 16 68 40 68 Q 64 68 64 42 Z" fill="url(#gradBowl)"/>
    <!-- Straw -->
    <line x1="48" y1="14" x2="38" y2="44" stroke="#EF4444" stroke-width="4" stroke-linecap="round"/>
    <line x1="45" y1="18" x2="41" y2="30" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/>
  </g>
  <!-- Text Brand -->
  <text x="100" y="46" font-family="'Plus Jakarta Sans', 'Segoe UI', sans-serif" font-weight="900" font-size="28" fill="#0284C7" letter-spacing="-0.5">
    ES TELER <tspan fill="#10B981">JUARA 77</tspan>
  </text>
  <text x="101" y="68" font-family="'Plus Jakarta Sans', 'Segoe UI', sans-serif" font-weight="600" font-size="12" fill="#64748B" letter-spacing="1.5">
    SENSASI KESEGARAN ASLI NUSANTARA
  </text>
</svg>"""

with open(os.path.join(img_dir, "logo.svg"), "w", encoding="utf-8") as f:
    f.write(logo_svg)

# Generator for Food/Drink SVG Cards
def generate_menu_svg(title, category, color_from, color_to, emoji_icon):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color_from}" />
      <stop offset="100%" stop-color="{color_to}" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000" flood-opacity="0.12"/>
    </filter>
  </defs>
  <rect width="400" height="300" rx="16" fill="url(#bgGrad)"/>
  <!-- Decorative Circles -->
  <circle cx="340" cy="60" r="80" fill="#ffffff" opacity="0.1"/>
  <circle cx="60" cy="240" r="70" fill="#ffffff" opacity="0.08"/>
  <!-- Main Display Card -->
  <g transform="translate(140, 60)" filter="url(#shadow)">
    <circle cx="60" cy="60" r="55" fill="#ffffff"/>
    <text x="60" y="78" font-size="52" text-anchor="middle">{emoji_icon}</text>
  </g>
  <!-- Text info -->
  <rect x="30" y="200" width="340" height="74" rx="12" fill="#ffffff" opacity="0.95"/>
  <text x="200" y="232" font-family="'Segoe UI', sans-serif" font-weight="bold" font-size="18" fill="#0F172A" text-anchor="middle">{title}</text>
  <text x="200" y="256" font-family="'Segoe UI', sans-serif" font-weight="600" font-size="12" fill="#0284C7" text-anchor="middle">{category.upper()}</text>
</svg>"""

menu_items = [
    ("es_teler_original.jpg", "Es Teler Original Juara", "Spesial Es Teler", "#0284C7", "#06B6D4", "🥑"),
    ("es_teler_durian.jpg", "Es Teler Durian Sultan", "Spesial Es Teler", "#F59E0B", "#10B981", "👑"),
    ("es_teler_keju.jpg", "Es Teler Keju Melimpah", "Spesial Es Teler", "#FBBF24", "#0284C7", "🧀"),
    ("es_teler_alpukat_kocok.jpg", "Es Teler Alpukat Kocok", "Spesial Es Teler", "#84CC16", "#047857", "🥑"),
    ("es_kelapa_jeruk.jpg", "Es Kelapa Muda Jeruk", "Minuman Segar", "#F97316", "#0284C7", "🥥"),
    ("es_cincau_aren.jpg", "Es Cincau Susu Aren", "Aneka Es", "#78350F", "#D97706", "🧋"),
    ("es_kuwut_bali.jpg", "Es Kuwut Bali Segar", "Minuman Segar", "#10B981", "#06B6D4", "🍈"),
    ("es_campur.jpg", "Es Campur Segar Manis", "Aneka Es", "#EC4899", "#8B5CF6", "🍧"),
    ("jus_alpukat.jpg", "Jus Alpukat Mentega", "Jus Segar", "#65A30D", "#15803D", "🥤"),
    ("es_lemon_tea.jpg", "Es Lemon Tea Mint", "Minuman Segar", "#EAB308", "#10B981", "🍋"),
    ("pisang_crispy.jpg", "Pisang Crispy Keju", "Camilan", "#D97706", "#F59E0B", "🍌"),
    ("roti_bakar.jpg", "Roti Bakar Cokelat Keju", "Camilan", "#92400E", "#B45309", "🍞"),
    ("cireng_rujak.jpg", "Cireng Krispy Rujak", "Camilan", "#DC2626", "#F97316", "🥟"),
    ("kentang_keju.jpg", "Kentang Goreng Keju", "Camilan", "#F59E0B", "#FBBF24", "🍟"),
    ("default_menu.jpg", "Menu Segar Nusantara", "Es Teler Juara", "#0284C7", "#10B981", "🍨")
]

for filename, title, category, c1, c2, emoji in menu_items:
    content = generate_menu_svg(title, category, c1, c2, emoji)
    # Save as svg or jpg filename for compatibility with db seed
    with open(os.path.join(uploads_dir, filename), "w", encoding="utf-8") as f:
        f.write(content)
    with open(os.path.join(img_dir, filename), "w", encoding="utf-8") as f:
        f.write(content)

print("SVG assets generated successfully!")
