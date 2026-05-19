// CLOCK JS
(function updateClock() {
    const el = document.getElementById('clock');
    if (el) {
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, '0');
        const mm = String(now.getMinutes()).padStart(2, '0');
        const ss = String(now.getSeconds()).padStart(2, '0');
        el.textContent = hh + ':' + mm + ':' + ss;
    }
    setTimeout(updateClock, 1000);
})();

// DASHBOARD JS
document.addEventListener('DOMContentLoaded', function () {
    const dropdowns = [
        { menu: document.getElementById('menu-he-thong'), drop: document.getElementById('dropdown-he-thong') },
        { menu: document.getElementById('menu-quan-ly'), drop: document.getElementById('dropdown-quan-ly') },
        { menu: document.getElementById('menu-thong-ke'), drop: document.getElementById('dropdown-thong-ke') }
    ];

    dropdowns.forEach(item => {
        if (item.menu && item.drop) {
            item.menu.addEventListener('click', function (e) {
                e.preventDefault();

                dropdowns.forEach(otherItem => {
                    if (otherItem !== item) {
                        otherItem.drop.classList.remove('show');
                        otherItem.menu.classList.remove('active');
                    }
                });

                item.drop.classList.toggle('show');
                item.menu.classList.toggle('active');
            });
        }
    });

    document.addEventListener('click', function (e) {
        dropdowns.forEach(item => {
            if (item.menu && item.drop && !item.menu.contains(e.target) && !item.drop.contains(e.target)) {
                item.drop.classList.remove('show');
                item.menu.classList.remove('active');
            }
        });
    });
});
// LOGIN JS
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('loginForm');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const user = (document.getElementById('_010_txtTaiKhoan') || {}).value || '';
        const pass = (document.getElementById('_010_txtMatKhau') || {}).value || '';
        const VALID_USERNAME = 'admin';
        const VALID_PASSWORD = 'admin123';

        if (user.trim() === VALID_USERNAME && pass === VALID_PASSWORD) {
            window.location.href = 'Dashboard.html';
        } else {
            alert('Tài khoản hoặc mật khẩu không đúng');
        }
    });
});
// PRICING JS
document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('totalCount')) return;

    let data = [
        { type: 'Xe Máy', price_turn: 5000, time_in: '06:00', time_out: '22:00', note: 'Thường ngày' },
        { type: 'Xe Tay Ga', price_turn: 5000, time_in: '06:00', time_out: '22:00', note: 'Thường ngày' },
        { type: 'Ô tô', price_turn: 15000, time_in: '06:00', time_out: '22:00', note: '' },
    ];
    let selectedIdx = null;
    let filterText = '';

    function fmtPrice(n) { return Number(n).toLocaleString('vi-VN') + 'đ'; }

    function renderTable() {
        const tbody = document.getElementById('tableBody');
        if (!tbody) return;
        const totalEl = document.getElementById('totalCount');
        if (totalEl) totalEl.textContent = data.length;
        const summaryEl = document.getElementById('summaryRow');
        if (summaryEl) summaryEl.textContent = 'Tổng cộng: ' + data.length + ' loại xe đang hoạt động';
        let rows = data.filter(d => d.type.toLowerCase().includes(filterText.toLowerCase()));
        tbody.innerHTML = rows.map(d => {
            const realIdx = data.indexOf(d);
            const sel = realIdx === selectedIdx ? 'selected' : '';
            return `<tr class="${sel}" onclick="selectRow(${realIdx})">
                <td>${realIdx + 1}</td>
                <td>${d.type}</td>
                <td><span class="price-tag">${fmtPrice(d.price_turn)}</span></td>
                <td><span class="time-badge">${d.time_in}</span></td>
                <td><span class="time-badge">${d.time_out}</span></td>
            </tr>`;
        }).join('');
    }

    function showStatus(msg, color) {
        const el = document.getElementById('statusMsg');
        if (!el) return;
        el.style.color = color || '#27ae60';
        el.textContent = msg;
        setTimeout(() => { el.textContent = ''; }, 2500);
    }

    window.selectRow = function (idx) {
        selectedIdx = idx;
        const d = data[idx];
        document.getElementById('f_type').value = d.type;
        document.getElementById('f_price_turn').value = d.price_turn;
        document.getElementById('f_time_in').value = d.time_in;
        document.getElementById('f_time_out').value = d.time_out;
        renderTable();
    };
    window.addOrUpdate = function () {
        const obj = {
            type: document.getElementById('f_type').value,
            price_turn: parseInt(document.getElementById('f_price_turn').value) || 0,
            time_in: document.getElementById('f_time_in').value,
            time_out: document.getElementById('f_time_out').value,
            note: document.getElementById('f_note').value,
        };
        if (selectedIdx !== null) { data[selectedIdx] = obj; showStatus('Đã cập nhật thành công!'); }
        else { data.push(obj); selectedIdx = data.length - 1; showStatus('Đã thêm loại xe mới!'); }
        renderTable();
    };
    window.deleteRow = function () {
        if (selectedIdx === null) { showStatus('Chọn một hàng để xóa.', '#e74c3c'); return; }
        data.splice(selectedIdx, 1);
        selectedIdx = null;
        window.clearForm();
        showStatus('Đã xóa!', '#e74c3c');
    };
    window.clearForm = function () {
        selectedIdx = null;
        document.getElementById('f_type').value = 'Xe Máy';
        document.getElementById('f_price_turn').value = '';
        document.getElementById('f_time_in').value = '06:00';
        document.getElementById('f_time_out').value = '22:00';
        document.getElementById('f_note').value = '';
        renderTable();
    };
    window.filterTable = function () {
        filterText = document.getElementById('searchInput').value;
        renderTable();
    };
    window.resetFilter = function () {
        document.getElementById('searchInput').value = '';
        filterText = '';
        renderTable();
    };

    renderTable();
});

// REPORT JS
document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('donutChart')) return;

    const tableData = [
        { name: 'Xe Đạp',       doanhthu: 0,      vao: 0,   ra: 0,   highlight: true },
        { name: 'Xe Điện',      doanhthu: 0,      vao: 0,   ra: 0   },
        { name: 'Xe Tay Ga',    doanhthu: 0,      vao: 180, ra: 242 },
        { name: 'Ô tô',         doanhthu: 0,      vao: 3,   ra: 2   },
        { name: 'Xe Máy',       doanhthu: 145000, vao: 88,  ra: 100 },
        { name: 'Ô tô 5 chỗ',  doanhthu: 0,      vao: 11,  ra: 18  },
        { name: 'Ô tô 7 chỗ',  doanhthu: 0,      vao: 0,   ra: 1   },
        { name: 'Ô tô bán tải', doanhthu: 0,      vao: 0,   ra: 1   },
    ];

    function fmtNum(n) { return n === 0 ? '<span style="color:#aab">0</span>' : Number(n).toLocaleString('vi-VN'); }
    function fmtMoney(n) { return n === 0 ? '<span style="color:#aab">0</span>' : `<span style="color:#e74c3c;font-weight:600">${Number(n).toLocaleString('vi-VN')}</span>`; }

    function renderReportTable() {
        const tbody = document.getElementById('tableBody');
        if (!tbody) return;
        let t = { doanhthu: 0, vao: 0, ra: 0 };
        tbody.innerHTML = tableData.map(d => {
            t.doanhthu += d.doanhthu; t.vao += d.vao; t.ra += d.ra;
            return `<tr class="${d.highlight ? 'highlight' : ''}">
                <td class="col-name">${d.name}</td>
                <td>${fmtMoney(d.doanhthu)}</td>
                <td>${fmtNum(d.vao)}</td>
                <td>${fmtNum(d.ra)}</td>
            </tr>`;
        }).join('');
        tbody.innerHTML += `<tr class="total-row">
            <td class="col-name" style="color:#e74c3c">Tổng</td>
            <td style="color:#e91e8c;font-weight:700">${Number(t.doanhthu).toLocaleString('vi-VN')}đ</td>
            <td style="color:#2980b9;font-weight:700">${t.vao}</td>
            <td style="color:#2980b9;font-weight:700">${t.ra}</td>
        </tr>`;
    }

    function renderDonut() {
        const colors = ['#2980b9','#1abc9c','#e91e8c','#f39c12','#8e44ad','#e74c3c','#16a085','#d35400'];
        const withRevenue = tableData.filter(d => d.doanhthu > 0);
        const labels = withRevenue.length ? withRevenue.map(d => d.name) : ['Xe Máy'];
        const vals   = withRevenue.length ? withRevenue.map(d => d.doanhthu) : [145000];
        new Chart(document.getElementById('donutChart').getContext('2d'), {
            type: 'doughnut',
            data: { labels, datasets: [{ data: vals, backgroundColor: colors.slice(0, vals.length), borderWidth: 2, borderColor: '#fff', hoverOffset: 6 }] },
            options: { cutout: '62%', plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.label}: ${Number(c.raw).toLocaleString('vi-VN')}đ` } } } }
        });
        document.getElementById('donutLegend').innerHTML = labels.map((l, i) =>
            `<div class="legend-item"><span class="legend-dot" style="background:${colors[i]}"></span>${l}</div>`).join('');
    }

    function renderBar() {
        if (!document.getElementById('barChart')) return;
        new Chart(document.getElementById('barChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['24/03','25/03','26/03','27/03','28/03','29/03','30/03'],
                datasets: [{ label: 'Xe Máy', data: [460,370,300,365,355,95,240], backgroundColor: '#2980b9', borderRadius: 4, hoverBackgroundColor: '#1a5276' }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: true, labels: { font: { size: 11 }, color: '#5d6d7e' } } },
                scales: {
                    x: { grid: { color: '#eaecee' }, ticks: { font: { size: 11 }, color: '#5d6d7e' } },
                    y: { grid: { color: '#eaecee' }, ticks: { font: { size: 11 }, color: '#5d6d7e', callback: v => v + 'K' } }
                }
            }
        });
    }

    renderReportTable();
    renderDonut();
    renderBar();
});
