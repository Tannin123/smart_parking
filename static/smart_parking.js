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
    // Sidebar menu active state
    const menuItems = document.querySelectorAll('.menu-item');
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    menuItems.forEach(item => {
        const href = item.getAttribute('onclick') || '';
        if (href.includes(currentPage) || 
            (currentPage === '' && href.includes('Dashboard.html')) ||
            (currentPage === 'nhandien.html' && href.includes('nhandien.html')) ||
            (currentPage === 'report.html' && href.includes('report.html')) ||
            (currentPage === 'login.html' && href.includes('login.html'))) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

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

/* ── NHẬN DIỆN PAGE: TAB SWITCHING ────────────────────── */
function switchTab(name, btn) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    btn.classList.add('active');
    if (name !== 'webcam') stopWebcam();
}

/* ── RESULT HELPERS ─────────────────────────────────────── */
function showResultContent() {
    document.getElementById('resultEmpty').style.display   = 'none';
    document.getElementById('resultError').style.display   = 'none';
    document.getElementById('resultContent').style.display = 'flex';
    document.getElementById('btnReset').disabled = false;
}

function showResultError(msg) {
    document.getElementById('resultEmpty').style.display   = 'none';
    document.getElementById('resultContent').style.display = 'none';
    document.getElementById('resultError').style.display   = 'block';
    document.getElementById('resultErrorText').textContent = msg;
    document.getElementById('resultSubtitle').textContent  = 'Đã xảy ra lỗi';
    document.getElementById('btnReset').disabled = false;
}

function clearResult() {
    document.getElementById('resultEmpty').style.display   = 'flex';
    document.getElementById('resultContent').style.display = 'none';
    document.getElementById('resultError').style.display   = 'none';
    document.getElementById('resultSubtitle').textContent  = 'Chưa có kết quả — hãy chọn ảnh hoặc video';
    document.getElementById('btnReset').disabled = true;
    document.getElementById('resultImage').style.display   = 'none';
    document.getElementById('resultInfo').style.display    = 'none';
    document.getElementById('resultDownload').style.display= 'none';
}

/* ── IMAGE ──────────────────────────────────────────────── */
let selectedImageFile = null;

function onImageSelected(e) {
    selectedImageFile = e.target.files[0];
    if (!selectedImageFile) return;

    const preview = document.getElementById('imgPreview');
    preview.src = URL.createObjectURL(selectedImageFile);
    preview.style.display = 'block';

    const area = document.getElementById('uploadAreaImg');
    area.classList.add('has-file');
    area.querySelector('.up-title').textContent = selectedImageFile.name;
    area.querySelector('.up-hint').textContent  = (selectedImageFile.size / 1024).toFixed(0) + ' KB';

    document.getElementById('btnDetectImg').disabled = false;
    clearResult();
}

async function detectImage() {
    if (!selectedImageFile) return;
    const btn  = document.getElementById('btnDetectImg');
    const icon = document.getElementById('iconImg');
    btn.disabled = true;
    icon.className = 'fa-solid fa-spinner fa-spin';
    try {
        const formData = new FormData();
        formData.append('image', selectedImageFile);
        const res    = await fetch('/api/detect/image', { method: 'POST', body: formData });
        const result = await res.json();
        if (result.success) {
            showImageResult(result);
        } else {
            showResultError(result.error || 'Có lỗi xảy ra khi nhận diện.');
        }
    } catch {
        showResultError('Lỗi kết nối máy chủ.');
    } finally {
        btn.disabled = false;
        icon.className = 'fa-solid fa-magnifying-glass';
    }
}

function showImageResult(result) {
    showResultContent();
    const platesEl = document.getElementById('resultPlates');
    if (result.plates && result.plates.length > 0) {
        platesEl.innerHTML = result.plates.map(p => {
            const txt = p.text || '(không đọc được)';
            return `<div class="plate-action-group">
                <span class="plate-tag"><i class="fa-solid fa-car"></i>${txt}</span>
                <button class="btn-checkin" onclick="handleCheckIn('${txt}')">Cho Xe Vào</button>
                <button class="btn-checkout" onclick="handleCheckOut('${txt}')">Cho Xe Ra</button>
            </div>`;
        }).join('');
        document.getElementById('resultSubtitle').textContent = `Tìm thấy ${result.plates.length} biển số`;
    } else {
        platesEl.innerHTML = '<span style="font-size:11px;color:#94a3b8;font-family:Inter,sans-serif">Không tìm thấy biển số trong ảnh.</span>';
        document.getElementById('resultSubtitle').textContent = 'Không tìm thấy biển số';
    }
    if (result.annotated_b64) {
        const img = document.getElementById('resultImage');
        img.src = 'data:image/jpeg;base64,' + result.annotated_b64;
        img.style.display = 'block';
    }
}

/* ── VIDEO ──────────────────────────────────────────────── */
let selectedVideoFile = null;

function onVideoSelected(e) {
    selectedVideoFile = e.target.files[0];
    if (!selectedVideoFile) return;
    const area = document.getElementById('uploadAreaVideo');
    area.classList.add('has-file');
    area.querySelector('.up-title').textContent = selectedVideoFile.name;
    area.querySelector('.up-hint').textContent  = (selectedVideoFile.size / 1024 / 1024).toFixed(1) + ' MB';
    const fi = document.getElementById('videoFileInfo');
    fi.style.display = 'flex';
    document.getElementById('videoFilename').textContent = selectedVideoFile.name;
    document.getElementById('btnDetectVideo').disabled = false;
    clearResult();
}

async function detectVideo() {
    if (!selectedVideoFile) return;
    const btn  = document.getElementById('btnDetectVideo');
    const icon = document.getElementById('iconVideo');
    btn.disabled = true;
    btn.childNodes[1].textContent = ' Đang xử lý…';
    icon.className = 'fa-solid fa-spinner fa-spin';
    try {
        const formData = new FormData();
        formData.append('video', selectedVideoFile);
        const res    = await fetch('/api/detect/video', { method: 'POST', body: formData });
        const result = await res.json();
        if (result.success) {
            showVideoResult(result);
        } else {
            showResultError(result.error || 'Có lỗi xảy ra khi xử lý video.');
        }
    } catch {
        showResultError('Lỗi kết nối máy chủ.');
    } finally {
        btn.disabled = false;
        btn.childNodes[1].textContent = ' Xử Lý Video';
        icon.className = 'fa-solid fa-play';
    }
}

function showVideoResult(result) {
    showResultContent();
    const platesEl = document.getElementById('resultPlates');
    if (result.plates && result.plates.length > 0) {
        platesEl.innerHTML = result.plates.map(p => {
            return `<div class="plate-action-group">
                <span class="plate-tag"><i class="fa-solid fa-car"></i>${p}</span>
                <button class="btn-checkin" onclick="handleCheckIn('${p}')">Cho Xe Vào</button>
                <button class="btn-checkout" onclick="handleCheckOut('${p}')">Cho Xe Ra</button>
            </div>`;
        }).join('');
        document.getElementById('resultSubtitle').textContent = `Tìm thấy ${result.plates.length} biển số`;
    } else {
        platesEl.innerHTML = '<span style="font-size:11px;color:#94a3b8;font-family:Inter,sans-serif">Không tìm thấy biển số trong video.</span>';
        document.getElementById('resultSubtitle').textContent = 'Không tìm thấy biển số';
    }
    const infoEl = document.getElementById('resultInfo');
    infoEl.style.display = 'flex';
    document.getElementById('resultInfoText').textContent = `Đã xử lý ${result.total_frames} frames`;
    if (result.output_path) {
        const dl = document.getElementById('resultDownload');
        dl.href = '/' + result.output_path;
        dl.style.display = 'flex';
    }
}

/* ── WEBCAM ─────────────────────────────────────────────── */
let webcamActive   = false;
let _webcamPollId  = null;   // setInterval ID cho result polling

function startWebcam() {
    webcamActive = true;
    const feed        = document.getElementById('webcamFeed');
    const placeholder = document.getElementById('webcamPlaceholder');
    feed.src = '/api/detect/webcam/stream';
    feed.style.display        = 'block';
    placeholder.style.display = 'none';
    document.getElementById('btnStartCam').style.display = 'none';
    document.getElementById('btnStopCam').style.display  = 'flex';

    // Hiện panel kết quả ở trạng thái chờ
    showResultContent();
    document.getElementById('resultSubtitle').textContent = 'Đang chờ nhận diện…';
    document.getElementById('resultPlates').innerHTML =
        '<span style="font-size:11px;color:#94a3b8;font-family:Inter,sans-serif">Camera đang quét biển số…</span>';
    document.getElementById('resultImage').style.display  = 'none';
    document.getElementById('resultInfo').style.display   = 'none';
    document.getElementById('resultDownload').style.display = 'none';

    // Polling kết quả mỗi 1 giây
    _webcamPollId = setInterval(_pollWebcamResult, 1000);
}

async function _pollWebcamResult() {
    if (!webcamActive) return;
    try {
        const res    = await fetch('/api/detect/webcam/result');
        const result = await res.json();
        if (!result.success) return;

        const platesEl = document.getElementById('resultPlates');
        if (result.plates && result.plates.length > 0) {
            platesEl.innerHTML = result.plates.map(p => {
                return `<div class="plate-action-group">
                    <span class="plate-tag"><i class="fa-solid fa-car"></i>${p.text}</span>
                    <button class="btn-checkin" onclick="handleCheckIn('${p.text}')">Cho Xe Vào</button>
                    <button class="btn-checkout" onclick="handleCheckOut('${p.text}')">Cho Xe Ra</button>
                </div>`;
            }).join('');
            document.getElementById('resultSubtitle').textContent =
                `Tìm thấy ${result.plates.length} biển số`;
        } else {
            platesEl.innerHTML =
                '<span style="font-size:11px;color:#94a3b8;font-family:Inter,sans-serif">Đang quét… giữ biển số trước camera</span>';
            document.getElementById('resultSubtitle').textContent = 'Đang chờ nhận diện…';
        }
    } catch (_) { /* bỏ qua lỗi mạng tạm thời */ }
}

function stopWebcam() {
    if (!webcamActive) return;
    webcamActive = false;

    // Dừng polling
    if (_webcamPollId) {
        clearInterval(_webcamPollId);
        _webcamPollId = null;
    }

    const feed        = document.getElementById('webcamFeed');
    const placeholder = document.getElementById('webcamPlaceholder');
    feed.src = '';
    feed.style.display        = 'none';
    placeholder.style.display = 'flex';
    document.getElementById('btnStartCam').style.display = 'flex';
    document.getElementById('btnStopCam').style.display  = 'none';
}

/* ── PARKING LOGIC ────────────────────────────────────────── */

async function handleCheckIn(plate) {
    if (!plate || plate.includes('không')) return;
    try {
        const res = await fetch('/api/parking/in', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({plate: plate})
        });
        const result = await res.json();
        if (result.success) {
            alert("Thành công: " + result.message);
            loadParkingHistory();
        } else {
            alert("Lỗi: " + result.error + (result.message ? " - " + result.message : ""));
        }
    } catch (e) {
        alert("Lỗi kết nối máy chủ.");
    }
}

async function handleCheckOut(plate) {
    if (!plate || plate.includes('không')) return;
    try {
        const res = await fetch('/api/parking/out', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({plate: plate})
        });
        const result = await res.json();
        if (result.success) {
            alert("Thành công: " + result.message);
            loadParkingHistory();
        } else {
            alert("Lỗi: " + result.error + (result.message ? " - " + result.message : ""));
        }
    } catch (e) {
        alert("Lỗi kết nối máy chủ.");
    }
}

async function loadParkingHistory() {
    const listEl = document.getElementById('parkingHistoryList');
    if (!listEl) return;
    try {
        const res = await fetch('/api/parking/history');
        const result = await res.json();
        if (result.success && result.logs) {
            listEl.innerHTML = result.logs.map(log => {
                const color = log.status === 'IN' ? '#22c55e' : '#ef4444';
                const timeStr = log.status === 'IN' ? log.time_in : log.time_out;
                return `
                    <div class="vehicle-card" style="border-left: 3px solid ${color}">
                        <div class="vc-main">
                            <span class="vc-plate">${log.plate}</span>
                            <span class="vc-time" style="color:${color}">${log.status}</span>
                        </div>
                        <div class="vc-sub">${timeStr}</div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        console.error("Lỗi lấy lịch sử bãi xe", e);
    }
}

// Khởi tạo lịch sử bãi xe khi trang tải xong
document.addEventListener('DOMContentLoaded', () => {
    loadParkingHistory();
});

