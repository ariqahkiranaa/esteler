// main.js - Core UI Interactions & Utility Functions

document.addEventListener('DOMContentLoaded', function () {
  // 1. Sidebar Toggle
  const sidebar = document.querySelector('.sidebar');
  const toggleBtn = document.querySelector('.btn-sidebar-toggle');
  
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }

  // Close sidebar on clicking outside in mobile view
  document.addEventListener('click', function (e) {
    if (window.innerWidth <= 992 && sidebar && sidebar.classList.contains('show')) {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('show');
      }
    }
  });

  // 2. Live Date & Time Clock
  function updateClock() {
    const clockEl = document.getElementById('liveClock');
    if (!clockEl) return;
    
    const now = new Date();
    const days = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    
    const dayName = days[now.getDay()];
    const date = now.getDate();
    const monthName = months[now.getMonth()];
    const year = now.getFullYear();
    
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    clockEl.innerHTML = `<i class="bi bi-clock me-1 text-primary"></i> ${dayName}, ${date} ${monthName} ${year} &bull; ${hours}:${minutes}:${seconds} WIB`;
  }

  updateClock();
  setInterval(updateClock, 1000);

  // 3. Auto dismiss Bootstrap alerts after 5 seconds
  const autoAlerts = document.querySelectorAll('.alert-dismissible');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });
});

// Utility to format Indonesian Rupiah
function formatRupiah(number) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(number);
}
