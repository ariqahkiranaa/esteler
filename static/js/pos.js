// pos.js - Kasir Point of Sale System Logic

let cart = [];
let discount = 0;
let tax = 0;
let selectedMemberId = null;
let currentTransactionData = null;

document.addEventListener('DOMContentLoaded', function () {
  initPOS();
});

function initPOS() {
  // Category Filter Pills
  const categoryPills = document.querySelectorAll('.category-pill');
  categoryPills.forEach(pill => {
    pill.addEventListener('click', function () {
      categoryPills.forEach(p => p.classList.remove('active'));
      this.classList.add('active');
      const catId = this.getAttribute('data-cat');
      filterMenu(catId, document.getElementById('searchMenu').value);
    });
  });

  // Search input filter
  const searchInput = document.getElementById('searchMenu');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      const activePill = document.querySelector('.category-pill.active');
      const catId = activePill ? activePill.getAttribute('data-cat') : 'all';
      filterMenu(catId, this.value);
    });
  }

  // Member select change
  const memberSelect = document.getElementById('selectMember');
  if (memberSelect) {
    memberSelect.addEventListener('change', function () {
      selectedMemberId = this.value ? parseInt(this.value) : null;
      const opt = this.options[this.selectedIndex];
      const memberInfoBadge = document.getElementById('memberInfoBadge');
      if (this.value) {
        const poin = opt.getAttribute('data-poin') || 0;
        memberInfoBadge.innerHTML = `<span class="badge bg-success-subtle text-success"><i class="bi bi-star-fill text-warning me-1"></i>Poin: ${poin}</span>`;
      } else {
        memberInfoBadge.innerHTML = '';
      }
    });
  }

  // Discount input change
  const discountInput = document.getElementById('inputDiskon');
  if (discountInput) {
    discountInput.addEventListener('input', function () {
      discount = parseFloat(this.value) || 0;
      renderCart();
    });
  }

  // Payment cash input calculation
  const bayarInput = document.getElementById('modalBayarInput');
  if (bayarInput) {
    bayarInput.addEventListener('input', calculateChange);
  }

  // Payment method pills
  const paymentMethods = document.querySelectorAll('input[name="paymentMethod"]');
  paymentMethods.forEach(method => {
    method.addEventListener('change', function () {
      const qrisBox = document.getElementById('qrisBox');
      const transferBox = document.getElementById('transferBox');
      const cashBox = document.getElementById('cashBox');
      
      if (qrisBox) qrisBox.classList.add('d-none');
      if (transferBox) transferBox.classList.add('d-none');
      if (cashBox) cashBox.classList.add('d-none');

      if (this.value === 'QRIS' && qrisBox) {
        qrisBox.classList.remove('d-none');
        setExactPayment();
      } else if (this.value === 'Transfer' && transferBox) {
        transferBox.classList.remove('d-none');
        setExactPayment();
      } else if (this.value === 'Debit') {
        setExactPayment();
      } else if (cashBox) {
        cashBox.classList.remove('d-none');
      }
    });
  });
}

function filterMenu(catId, query) {
  const q = (query || '').toLowerCase().trim();
  const items = document.querySelectorAll('.pos-item-card');

  items.forEach(item => {
    const itemCat = item.getAttribute('data-cat-id');
    const itemName = item.getAttribute('data-name').toLowerCase();
    const itemCode = item.getAttribute('data-code').toLowerCase();

    const matchesCat = (catId === 'all' || itemCat === catId);
    const matchesQuery = !q || itemName.includes(q) || itemCode.includes(q);

    if (matchesCat && matchesQuery) {
      item.parentElement.style.display = 'block';
    } else {
      item.parentElement.style.display = 'none';
    }
  });
}

function addToCart(menuId, kode, nama, harga, status) {
  if (status === 'Habis') {
    Swal.fire({
      icon: 'warning',
      title: 'Menu Tidak Tersedia',
      text: `Maaf, stok ${nama} saat ini sedang habis.`,
      confirmButtonColor: '#0284C7'
    });
    return;
  }

  const existingIndex = cart.findIndex(i => i.menu_id === menuId);
  if (existingIndex > -1) {
    cart[existingIndex].qty += 1;
  } else {
    cart.push({
      menu_id: menuId,
      kode_menu: kode,
      nama_menu: nama,
      harga: parseFloat(harga),
      qty: 1,
      catatan_item: ''
    });
  }

  renderCart();
}

function updateQty(index, delta) {
  if (cart[index]) {
    cart[index].qty += delta;
    if (cart[index].qty <= 0) {
      cart.splice(index, 1);
    }
    renderCart();
  }
}

function removeItem(index) {
  cart.splice(index, 1);
  renderCart();
}

function clearCart() {
  if (cart.length === 0) return;
  cart = [];
  discount = 0;
  const dInput = document.getElementById('inputDiskon');
  if (dInput) dInput.value = '';
  renderCart();
}

function renderCart() {
  const container = document.getElementById('cartItemsList');
  const countBadge = document.getElementById('cartTotalCount');
  const subtotalEl = document.getElementById('cartSubtotal');
  const discountEl = document.getElementById('cartDiscount');
  const totalEl = document.getElementById('cartTotal');
  const btnCheckout = document.getElementById('btnOpenCheckout');

  let subtotal = 0;
  let totalQty = 0;

  if (cart.length === 0) {
    container.innerHTML = `
      <div class="text-center py-5 text-muted">
        <i class="bi bi-cart-x fs-1 text-light-muted d-block mb-2"></i>
        <p class="mb-0 fw-semibold">Keranjang masih kosong</p>
        <small class="text-secondary">Pilih menu di samping untuk mulai transaksi</small>
      </div>
    `;
    if (btnCheckout) btnCheckout.disabled = true;
  } else {
    let html = '';
    cart.forEach((item, index) => {
      const lineSubtotal = item.harga * item.qty;
      subtotal += lineSubtotal;
      totalQty += item.qty;

      html += `
        <div class="cart-item">
          <div class="cart-item-info">
            <h6>${item.nama_menu}</h6>
            <span>${formatRupiah(item.harga)} x ${item.qty} = <strong class="text-primary">${formatRupiah(lineSubtotal)}</strong></span>
          </div>
          <div class="cart-qty-ctrl">
            <button type="button" class="cart-qty-btn" onclick="updateQty(${index}, -1)"><i class="bi bi-dash"></i></button>
            <span class="fw-bold px-1" style="min-width: 20px; text-align: center;">${item.qty}</span>
            <button type="button" class="cart-qty-btn" onclick="updateQty(${index}, 1)"><i class="bi bi-plus"></i></button>
            <button type="button" class="btn btn-sm text-danger p-0 ms-2" onclick="removeItem(${index})"><i class="bi bi-trash"></i></button>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
    if (btnCheckout) btnCheckout.disabled = false;
  }

  const finalTotal = Math.max(0, subtotal - discount);

  if (countBadge) countBadge.innerText = totalQty;
  if (subtotalEl) subtotalEl.innerText = formatRupiah(subtotal);
  if (discountEl) discountEl.innerText = formatRupiah(discount);
  if (totalEl) totalEl.innerText = formatRupiah(finalTotal);
}

function openCheckoutModal() {
  if (cart.length === 0) return;

  const subtotal = cart.reduce((sum, item) => sum + (item.harga * item.qty), 0);
  const finalTotal = Math.max(0, subtotal - discount);

  document.getElementById('modalTotalBayarDisplay').innerText = formatRupiah(finalTotal);
  document.getElementById('modalSubtotalDisplay').innerText = formatRupiah(subtotal);
  document.getElementById('modalDiskonDisplay').innerText = formatRupiah(discount);

  const bayarInput = document.getElementById('modalBayarInput');
  bayarInput.value = '';
  document.getElementById('modalKembalianDisplay').innerText = 'Rp 0';

  // Default to Tunai
  const cashRadio = document.getElementById('methodTunai');
  if (cashRadio) cashRadio.checked = true;
  document.getElementById('cashBox').classList.remove('d-none');
  const qrisBox = document.getElementById('qrisBox');
  if (qrisBox) qrisBox.classList.add('d-none');
  const transferBox = document.getElementById('transferBox');
  if (transferBox) transferBox.classList.add('d-none');

  const modal = new bootstrap.Modal(document.getElementById('checkoutModal'));
  modal.show();
  setTimeout(() => bayarInput.focus(), 500);
}

function setQuickCash(amount) {
  const subtotal = cart.reduce((sum, item) => sum + (item.harga * item.qty), 0);
  const finalTotal = Math.max(0, subtotal - discount);
  const bayarInput = document.getElementById('modalBayarInput');

  if (amount === 'pas') {
    bayarInput.value = finalTotal;
  } else {
    bayarInput.value = amount;
  }
  calculateChange();
}

function setExactPayment() {
  const subtotal = cart.reduce((sum, item) => sum + (item.harga * item.qty), 0);
  const finalTotal = Math.max(0, subtotal - discount);
  const bayarInput = document.getElementById('modalBayarInput');
  bayarInput.value = finalTotal;
  calculateChange();
}

function calculateChange() {
  const subtotal = cart.reduce((sum, item) => sum + (item.harga * item.qty), 0);
  const finalTotal = Math.max(0, subtotal - discount);
  const bayar = parseFloat(document.getElementById('modalBayarInput').value) || 0;
  const kembalian = bayar - finalTotal;

  const kembalianEl = document.getElementById('modalKembalianDisplay');
  const btnProcess = document.getElementById('btnSubmitTransaction');

  if (kembalian >= 0) {
    kembalianEl.innerText = formatRupiah(kembalian);
    kembalianEl.className = 'fw-bold text-success fs-5';
    btnProcess.disabled = false;
  } else {
    kembalianEl.innerText = `Kurang ${formatRupiah(Math.abs(kembalian))}`;
    kembalianEl.className = 'fw-bold text-danger fs-5';
    btnProcess.disabled = true;
  }
}

async function submitTransaction() {
  if (cart.length === 0) return;

  const subtotal = cart.reduce((sum, item) => sum + (item.harga * item.qty), 0);
  const finalTotal = Math.max(0, subtotal - discount);
  const bayar = parseFloat(document.getElementById('modalBayarInput').value) || 0;
  const kembalian = bayar - finalTotal;

  if (bayar < finalTotal) {
    Swal.fire({
      icon: 'error',
      title: 'Uang Bayar Kurang',
      text: 'Nominal pembayaran tidak boleh kurang dari total belanja.',
      confirmButtonColor: '#0284C7'
    });
    return;
  }

  const metode = document.querySelector('input[name="paymentMethod"]:checked').value;
  const customerName = document.getElementById('inputCustomerName').value.trim() || 'Pelanggan Umum';
  const catatan = document.getElementById('inputCatatanPesanan').value.trim();

  const payload = {
    member_id: selectedMemberId,
    nama_pelanggan: customerName,
    items: cart,
    subtotal: subtotal,
    diskon: discount,
    pajak: 0,
    total_akhir: finalTotal,
    metode_pembayaran: metode,
    bayar: bayar,
    kembalian: kembalian,
    catatan: catatan
  };

  const btnProcess = document.getElementById('btnSubmitTransaction');
  btnProcess.disabled = true;
  btnProcess.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Menyimpan...`;

  try {
    const response = await fetch('/api/transaksi/simpan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const res = await response.json();

    if (res.status === 'success') {
      currentTransactionData = res.data;

      // Close checkout modal
      const checkoutModalEl = document.getElementById('checkoutModal');
      const checkoutModal = bootstrap.Modal.getInstance(checkoutModalEl);
      if (checkoutModal) checkoutModal.hide();

      // Reset cart
      clearCart();
      document.getElementById('inputCustomerName').value = '';
      document.getElementById('inputCatatanPesanan').value = '';
      const memSel = document.getElementById('selectMember');
      if (memSel) memSel.value = '';
      selectedMemberId = null;

      // Show receipt modal
      showReceiptModal(res.data);
    } else {
      Swal.fire({
        icon: 'error',
        title: 'Gagal Memproses Transaksi',
        text: res.message || 'Terjadi kesalahan sistem',
        confirmButtonColor: '#0284C7'
      });
    }
  } catch (err) {
    console.error(err);
    Swal.fire({
      icon: 'error',
      title: 'Kesalahan Jaringan',
      text: 'Tidak dapat terhubung ke server',
      confirmButtonColor: '#0284C7'
    });
  } finally {
    btnProcess.disabled = false;
    btnProcess.innerHTML = `<i class="bi bi-check-circle me-1"></i> Proses & Selesaikan`;
  }
}

function showReceiptModal(trx) {
  const modalEl = document.getElementById('receiptModal');
  const bodyEl = document.getElementById('receiptContent');

  let itemsHtml = '';
  trx.items.forEach(it => {
    itemsHtml += `
      <div class="receipt-row">
        <span>${it.nama_menu} x${it.jumlah}</span>
        <span>${formatRupiah(it.subtotal)}</span>
      </div>
    `;
  });

  bodyEl.innerHTML = `
    <div class="receipt-wrapper" id="printableReceipt">
      <div class="receipt-header">
        <h5 class="fw-bold mb-1">${trx.shop.nama_toko}</h5>
        <div class="small">${trx.shop.alamat || ''}</div>
        <div class="small">Telp: ${trx.shop.no_telepon || ''}</div>
        <div class="receipt-divider"></div>
        <div class="fw-bold fs-4 text-primary">${trx.no_antrean}</div>
        <div class="small text-muted">No: ${trx.no_transaksi}</div>
        <div class="small text-muted">${trx.created_at}</div>
        <div class="small">Pelanggan: ${trx.nama_pelanggan}</div>
      </div>

      <div class="receipt-divider"></div>

      <div class="receipt-items">
        ${itemsHtml}
      </div>

      <div class="receipt-divider"></div>

      <div class="receipt-row">
        <span>Subtotal:</span>
        <span>${formatRupiah(trx.subtotal)}</span>
      </div>
      ${trx.diskon > 0 ? `
      <div class="receipt-row text-danger">
        <span>Diskon:</span>
        <span>-${formatRupiah(trx.diskon)}</span>
      </div>` : ''}
      <div class="receipt-row fw-bold fs-6">
        <span>TOTAL:</span>
        <span>${formatRupiah(trx.total_akhir)}</span>
      </div>
      <div class="receipt-row">
        <span>Bayar (${trx.metode_pembayaran}):</span>
        <span>${formatRupiah(trx.bayar)}</span>
      </div>
      <div class="receipt-row">
        <span>Kembalian:</span>
        <span>${formatRupiah(trx.kembalian)}</span>
      </div>

      <div class="receipt-divider"></div>

      <div class="receipt-footer">
        <div>${trx.shop.pesan_struk_footer ? trx.shop.pesan_struk_footer.replace(/\n/g, '<br>') : 'Terima Kasih Atas Kunjungan Anda!'}</div>
      </div>
    </div>
  `;

  // Set link to direct print / thermal window
  const printBtn = document.getElementById('btnPrintDirect');
  if (printBtn) {
    printBtn.onclick = function () {
      printThermalReceipt(trx.id);
    };
  }

  const receiptModal = new bootstrap.Modal(modalEl);
  receiptModal.show();
}

function printThermalReceipt(trxId) {
  const printUrl = `/transaksi/struk/${trxId}?auto_print=1`;
  const printWindow = window.open(printUrl, '_blank', 'width=450,height=650');
  if (printWindow) {
    printWindow.focus();
  }
}
