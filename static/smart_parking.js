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

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const user = (document.getElementById('_010_txtTaiKhoan') || {}).value || '';
        const pass = (document.getElementById('_010_txtMatKhau') || {}).value || '';
        
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: user, password: pass})
            });
            const data = await res.json();
            if (data.success) {
                window.location.href = 'Dashboard.html';
            } else {
                alert(data.message || 'Tài khoản hoặc mật khẩu không đúng');
            }
        } catch(err) {
            alert('Lỗi kết nối máy chủ!');
        }
    });
});
// PRICING JS
document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('totalCount')) return;

    let data = [];
    let selectedIdx = null;
    let filterText = '';

    function fmtPrice(n) { return Number(n).toLocaleString('vi-VN') + 'đ'; }

    async function fetchPricing() {
        try {
            const res = await fetch('/api/pricing');
            const result = await res.json();
            if (result.success) {
                data = result.data || [];
                renderTable();
            }
        } catch(e) { console.error('Lỗi tải giá vé:', e); }
    }

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
    window.addOrUpdate = async function () {
        const obj = {
            type: document.getElementById('f_type').value,
            price_turn: parseInt(document.getElementById('f_price_turn').value) || 0,
            time_in: document.getElementById('f_time_in').value,
            time_out: document.getElementById('f_time_out').value,
            note: document.getElementById('f_note') ? document.getElementById('f_note').value : '',
        };
        try {
            if (selectedIdx !== null) { 
                const id = data[selectedIdx].id;
                const res = await fetch('/api/pricing/' + id, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(obj)});
                const result = await res.json();
                if (result.success) { showStatus('Đã cập nhật thành công!'); fetchPricing(); clearForm(); }
            } else { 
                const res = await fetch('/api/pricing', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(obj)});
                const result = await res.json();
                if (result.success) { showStatus('Đã thêm loại xe mới!'); fetchPricing(); clearForm(); }
            }
        } catch(e) { showStatus('Lỗi máy chủ', '#e74c3c'); }
    };
    window.deleteRow = async function () {
        if (selectedIdx === null) { showStatus('Chọn một hàng để xóa.', '#e74c3c'); return; }
        const id = data[selectedIdx].id;
        try {
            const res = await fetch('/api/pricing/' + id, {method: 'DELETE'});
            const result = await res.json();
            if(result.success) {
                window.clearForm();
                fetchPricing();
                showStatus('Đã xóa!', '#e74c3c');
            }
        } catch(e) { showStatus('Lỗi máy chủ', '#e74c3c'); }
    };
    window.clearForm = function () {
        selectedIdx = null;
        document.getElementById('f_type').value = 'Xe Máy';
        document.getElementById('f_price_turn').value = '';
        document.getElementById('f_time_in').value = '06:00';
        document.getElementById('f_time_out').value = '22:00';
        if(document.getElementById('f_note')) document.getElementById('f_note').value = '';
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

    fetchPricing();
});

// REPORT JS
document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('donutChart')) return;

    // Thiết lập ngày mặc định là hôm nay
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;
    
    document.getElementById('fromDate').value = `${todayStr}T00:00`;
    document.getElementById('toDate').value = `${todayStr}T23:59`;

    let tableData = [];
    let barChartLabels = [];
    let barChartData = [];

    function fmtNum(n) { return n === 0 ? '<span style="color:#aab">0</span>' : Number(n).toLocaleString('vi-VN'); }
    function fmtMoney(n) { return n === 0 ? '<span style="color:#aab">0</span>' : `<span style="color:#e74c3c;font-weight:600">${Number(n).toLocaleString('vi-VN')}</span>`; }

    window.fetchReportData = async function() {
        const fromDate = document.getElementById('fromDate').value;
        const toDate = document.getElementById('toDate').value;
        try {
            const res = await fetch(`/api/report?from=${fromDate}&to=${toDate}`);
            const result = await res.json();
            if (result.success) {
                tableData = result.data.tableData || [];
                barChartLabels = result.data.barChartLabels || [];
                barChartData = result.data.barChartData || [];
                renderReportTable();
                renderDonut();
                renderBar();
            }
        } catch(e) {
            console.error('Lỗi lấy dữ liệu thống kê:', e);
        }
    }

    // Gán hàm cho nút bấm "Báo Cáo Tổng Quát"
    window.renderTable = window.fetchReportData;

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

    let donutChartInstance = null;
    function renderDonut() {
        const colors = ['#2980b9','#1abc9c','#e91e8c','#f39c12','#8e44ad','#e74c3c','#16a085','#d35400'];
        const withRevenue = tableData.filter(d => d.doanhthu > 0);
        const labels = withRevenue.length ? withRevenue.map(d => d.name) : ['Chưa có doanh thu'];
        const vals   = withRevenue.length ? withRevenue.map(d => d.doanhthu) : [1];
        
        const ctx = document.getElementById('donutChart').getContext('2d');
        if (donutChartInstance) {
            donutChartInstance.destroy();
        }
        
        donutChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: { labels, datasets: [{ data: vals, backgroundColor: colors.slice(0, vals.length), borderWidth: 2, borderColor: '#fff', hoverOffset: 6 }] },
            options: { cutout: '62%', plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.label}: ${Number(c.raw).toLocaleString('vi-VN')}đ` } } } }
        });
        document.getElementById('donutLegend').innerHTML = labels.map((l, i) =>
            `<div class="legend-item"><span class="legend-dot" style="background:${colors[i]}"></span>${l}</div>`).join('');
            
        // Cập nhật text ở giữa
        const totalRev = withRevenue.length ? withRevenue.reduce((sum, d) => sum + d.doanhthu, 0) : 0;
        document.getElementById('donutLabel').innerHTML = `Doanh Thu<br>${Number(totalRev).toLocaleString('vi-VN')}đ`;
    }

    let barChartInstance = null;
    function renderBar() {
        if (!document.getElementById('barChart')) return;
        const ctx = document.getElementById('barChart').getContext('2d');
        if (barChartInstance) {
            barChartInstance.destroy();
        }
        
        barChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: barChartLabels.length ? barChartLabels : ['Chưa có dữ liệu'],
                datasets: [{ label: 'Lượt xe vào', data: barChartData.length ? barChartData : [0], backgroundColor: '#2980b9', borderRadius: 4, hoverBackgroundColor: '#1a5276' }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: true, labels: { font: { size: 11 }, color: '#5d6d7e' } } },
                scales: {
                    x: { grid: { color: '#eaecee' }, ticks: { font: { size: 11 }, color: '#5d6d7e' } },
                    y: { grid: { color: '#eaecee' }, ticks: { font: { size: 11 }, color: '#5d6d7e', callback: v => v } }
                }
            }
        });
    }

    window.fetchReportData();
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

/* NHẬN DIỆN */

/* ── State ── */
let curSrc = 'webcam';           // 'image' | 'webcam'
let selectedFile = null;         // File object khi chọn ảnh
let lastDetectedPlate = '';      // Biển số nhận diện được gần nhất
let webcamPollId = null;         // ID của setInterval polling webcam result
let lastWebcamTimestamp = '';    // Tránh cập nhật trùng lặp
const MODES = [
  'SPACE : Xe đạp',
  'SPACE : Xe máy',
  'SPACE : Ô tô'
];
let modeIdx = 0;

/* ── Helpers ── */
function setAlert(msg, type) {
  const el = document.getElementById('alertMsg');
  if (!el) return;
  el.textContent = msg;
  el.className = 'warning-text ' + (type || 'info');
}

function fmtDateTime(str) {
  if (!str) return '—';
  const d = new Date(str.replace(' ', 'T'));
  if (isNaN(d)) return str;
  return d.toLocaleDateString('vi-VN') + ' ' + d.toLocaleTimeString('vi-VN');
}

function setScanLoading(on) {
  const btn = document.getElementById('scanBtn');
  const icon = document.getElementById('scanIcon');
  const lbl = document.getElementById('scanLabel');
  if (!btn || !icon || !lbl) return;
  btn.classList.toggle('loading', on);
  icon.className = on ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-magnifying-glass';
  lbl.textContent = on ? 'ĐANG XỬ LÝ...' : 'NHẬN DIỆN BIỂN SỐ';
}

function showProc(on, msg) {
  const ov = document.getElementById('procOverlay');
  if (!ov) return;
  ov.classList.toggle('show', on);
  if (msg) {
    const label = document.getElementById('procLabel');
    if (label) label.textContent = msg;
  }
}

function showElement(id) { const el = document.getElementById(id); if (el) el.style.display = 'block'; }
function hideElement(id) { const el = document.getElementById(id); if (el) el.style.display = 'none'; }

function updatePlate(plate) {
  lastDetectedPlate = plate || '';
  const plateEl = document.getElementById('plateDetected');
  if (plateEl) plateEl.textContent = plate || '— — — —';
  const hasPlate = !!plate;
  const btnIn = document.getElementById('btnIn');
  const btnOut = document.getElementById('btnOut');
  if (btnIn) btnIn.disabled = !hasPlate;
  if (btnOut) btnOut.disabled = !hasPlate;
}

function setSource(t) {
  if (curSrc === 'webcam' && t !== 'webcam') stopWebcamPoll();
  curSrc = t;

  ['image', 'webcam'].forEach(s => {
    const el = document.getElementById('src-' + s);
    if (el) el.classList.toggle('active', s === t);
  });

  const fw = document.getElementById('fileWrapper');
  const fi = document.getElementById('fileInput');
  if (t === 'image') {
    if (fi) fi.accept = 'image/*';
    if (fw) fw.classList.add('show');
  } else {
    if (fw) fw.classList.remove('show');
  }

  const badgeMap = { image: 'CAM-01 · ẢNH', webcam: 'CAM-01 · WEBCAM' };
  const badgeEl = document.getElementById('camBadge');
  if (badgeEl) badgeEl.textContent = badgeMap[t];
  const titleLeft = document.getElementById('camTitleLeft');
  if (titleLeft) titleLeft.textContent = t === 'webcam' ? 'Webcam - Nhận Diện' : 'Ảnh tải lên';

  hideElement('previewImg');
  hideElement('annotatedImg');
  hideElement('camPlaceholder');

  if (t === 'webcam') {
    showElement('webcamStream');
    const camLive = document.getElementById('camLive');
    if (camLive) camLive.classList.add('show');
    startWebcamPoll();
    setAlert('WEBCAM ĐANG TRỰC TIẾP — SẴN SÀNG NHẬN DIỆN', 'ok');
  } else {
    hideElement('webcamStream');
    const camLive = document.getElementById('camLive');
    if (camLive) camLive.classList.remove('show');
    if (!selectedFile) {
      showElement('camPlaceholder');
      setAlert('CHỌN FILE ĐỂ BẮT ĐẦU NHẬN DIỆN', 'info');
    }
  }

  selectedFile = null;
  updatePlate('');
}

function onStreamError() {
  const camLive = document.getElementById('camLive');
  if (camLive) camLive.classList.remove('show');
  hideElement('webcamStream');
  const ph = document.getElementById('camPlaceholder');
  if (ph) {
    const span = ph.querySelector('span');
    if (span) span.textContent = 'Không kết nối được webcam server';
    showElement('camPlaceholder');
  }
  setAlert('LỖI: KHÔNG KẾT NỐI ĐƯỢC WEBCAM', '');
}

function handleFile(inp) {
  const f = inp.files[0];
  if (!f) return;
  selectedFile = f;
  const url = URL.createObjectURL(f);
  hideElement('camPlaceholder');
  hideElement('annotatedImg');

  if (curSrc === 'image') {
    const img = document.getElementById('previewImg');
    if (img) {
      img.src = url;
      showElement('previewImg');
    }
    setAlert('ĐÃ TẢI ẢNH — NHẤN NHẬN DIỆN ĐỂ XỬ LÝ', 'info');
  }
  updatePlate('');
}

function doScan() {
  if (curSrc === 'image') doScanImage();
  else doScanWebcam();
}

async function doScanImage() {
  if (!selectedFile) { setAlert('HÃY CHỌN ẢNH TRƯỚC', ''); return; }
  setScanLoading(true);
  showProc(true, 'Đang nhận diện ảnh...');
  try {
    const fd = new FormData();
    fd.append('image', selectedFile);
    const res = await fetch('/api/detect/image', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success) {
      const plates = data.plates || [];
      const plate = plates.length ? plates[0].text : '';
      updatePlate(plate);
      if (data.annotated_b64) {
        const ai = document.getElementById('annotatedImg');
        if (ai) {
          ai.src = 'data:image/jpeg;base64,' + data.annotated_b64;
          hideElement('previewImg');
          showElement('annotatedImg');
        }
      }
      if (plate) {
        setAlert('ĐÃ NHẬN DIỆN: ' + plate, 'ok');
      } else {
        setAlert('KHÔNG TÌM THẤY BIỂN SỐ TRONG ẢNH', '');
      }
    } else {
      setAlert('LỖI: ' + (data.error || 'Không xác định'), '');
    }
  } catch {
    setAlert('LỖI KẾT NỐI MÁY CHỦ', '');
  } finally {
    setScanLoading(false);
    showProc(false);
  }
}

async function doScanWebcam() {
  setScanLoading(true);
  try {
    const res = await fetch('/api/detect/webcam/result');
    const data = await res.json();
    if (data.success && data.plates && data.plates.length) {
      const plate = data.plates[0].text;
      updatePlate(plate);
      setAlert('WEBCAM NHẬN DIỆN: ' + plate, 'ok');
    } else {
      setAlert('CHƯA PHÁT HIỆN BIỂN SỐ – GIỮ BIỂN SỐ TRƯỚC CAMERA', 'info');
    }
  } catch {
    setAlert('LỖI KẾT NỐI MÁY CHỦ', '');
  } finally {
    setScanLoading(false);
  }
}

function startWebcamPoll() {
  stopWebcamPoll();
  webcamPollId = setInterval(_pollWebcam, 1500);
}
function stopWebcamPoll() {
  if (webcamPollId) { clearInterval(webcamPollId); webcamPollId = null; }
}

async function _pollWebcam() {
  if (curSrc !== 'webcam') return;
  try {
    const res  = await fetch('/api/detect/webcam/result');
    const data = await res.json();
    if (!data.success) return;
    if (data.timestamp && data.timestamp === lastWebcamTimestamp) return;
    lastWebcamTimestamp = data.timestamp || '';
    if (data.plates && data.plates.length) {
      const plate = data.plates[0].text;
      updatePlate(plate);
      setAlert('WEBCAM PHÁT HIỆN: ' + plate, 'ok');
    }
  } catch { }
}

async function doCheckIn() {
  const plate = lastDetectedPlate;
  if (!plate) return;
  try {
    const res  = await fetch('/api/parking/in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate })
    });
    const data = await res.json();
    if (data.success) {
      setAlert('ĐÃ CHO XE VÀO: ' + plate, 'ok');
      const infoPlate = document.getElementById('info-plate');
      const infoIn = document.getElementById('info-in');
      const infoOut = document.getElementById('info-out');
      const infoStatus = document.getElementById('info-status');
      if (infoPlate) infoPlate.textContent = plate;
      if (infoIn) infoIn.textContent = fmtDateTime(new Date().toISOString());
      if (infoOut) infoOut.textContent = '—';
      if (infoStatus) infoStatus.textContent = '✓ TRONG BÃI';
      loadRecentHistory();
    } else {
      setAlert('LỖI: ' + (data.message || data.error || ''), '');
    }
  } catch {
    setAlert('LỖI KẾT NỐI MÁY CHỦ', '');
  }
}

async function doCheckOut() {
  const plate = lastDetectedPlate;
  if (!plate) return;
  try {
    const res  = await fetch('/api/parking/out', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate })
    });
    const data = await res.json();
    if (data.success) {
      const feeStr = data.fee ? Number(data.fee).toLocaleString('vi-VN') + ' VNĐ' : '0 VNĐ';
      setAlert('ĐÃ CHO XE RA: ' + plate + ' - Phí: ' + feeStr, 'ok');
      
      const feeVal = document.getElementById('feeVal');
      if (feeVal) feeVal.textContent = feeStr;
      
      const infoOut = document.getElementById('info-out');
      const infoStatus = document.getElementById('info-status');
      if (infoOut) infoOut.textContent = fmtDateTime(new Date().toISOString());
      if (infoStatus) infoStatus.textContent = '↩ ĐÃ RA';
      loadRecentHistory();
    } else {
      setAlert('LỖI: ' + (data.message || data.error || ''), '');
    }
  } catch {
    setAlert('LỖI KẾT NỐI MÁY CHỦ', '');
  }
}

function toggleMode() {
  modeIdx = (modeIdx + 1) % MODES.length;
  const btn = document.getElementById('modeBtn');
  if (btn) btn.textContent = MODES[modeIdx];
}

async function loadRecentHistory() {
  const tb = document.getElementById('recentBody');
  if (!tb) return;
  try {
    const res  = await fetch('/api/parking/history');
    const data = await res.json();
    if (data.success && data.logs && data.logs.length) {
      tb.innerHTML = data.logs.map(log => {
        const isIn = log.status === 'IN';
        return `<tr>
          <td class="plate-cell">${log.plate}</td>
          <td>${fmtDateTime(log.time_in)}</td>
          <td>${fmtDateTime(log.time_out)}</td>
          <td><span class="${isIn ? 'tag-vao' : 'tag-ra'}">${isIn ? '↓ Trong bãi' : '↑ Đã ra'}</span></td>
        </tr>`;
      }).join('');

      const latest = data.logs[0];
      const infoPlate = document.getElementById('info-plate');
      const infoIn = document.getElementById('info-in');
      const infoOut = document.getElementById('info-out');
      const infoStatus = document.getElementById('info-status');
      if (infoPlate) infoPlate.textContent = latest.plate;
      if (infoIn) infoIn.textContent = fmtDateTime(latest.time_in);
      if (infoOut) infoOut.textContent = fmtDateTime(latest.time_out);
      if (infoStatus) infoStatus.textContent = latest.status === 'IN' ? '✓ TRONG BÃI' : '↩ ĐÃ RA';
    } else {
      tb.innerHTML = '<tr><td class="empty-cell" colspan="4">Chưa có dữ liệu</td></tr>';
    }
  } catch {
    tb.innerHTML = '<tr><td class="empty-cell" colspan="4">Lỗi tải dữ liệu</td></tr>';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setSource('webcam');
  loadRecentHistory();
  setInterval(loadRecentHistory, 30000);
  document.addEventListener('keydown', e => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
      e.preventDefault();
      toggleMode();
    }
  });
});

/* EMPLOYEE PAGE LOGIC */
// EMPLOYEE PAGE LOGIC
document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('empTableBody')) return;

    let currentEmployees = [];
    let selectedId = null;

    async function fetchEmployees() {
        try {
            const res = await fetch('/api/users');
            const result = await res.json();
            if (result.success) {
                currentEmployees = result.data.map(u => ({
                    dbId: u.id,
                    id: u.username,
                    firstName: u.first_name || '',
                    lastName: u.last_name || '',
                    dob: u.dob || '',
                    gender: u.gender || 'Male',
                    address: u.address || ''
                }));
                renderTable();
            }
        } catch(e) { console.error('Lỗi tải nhân viên:', e); }
    }

    window.renderTable = function () {
        const tbody = document.getElementById('empTableBody');
        tbody.innerHTML = currentEmployees.map(e => `
            <tr class="${selectedId === e.dbId ? 'selected' : ''}" onclick="selectRow(${e.dbId})">
                <td class="emp-id">${e.id}</td>
                <td>${e.firstName}</td>
                <td>${e.lastName}</td>
                <td>${e.dob}</td>
                <td>
                    <span class="gender-badge ${e.gender === 'Male' ? 'male' : 'female'}">
                        <i class="ti ti-gender-${e.gender === 'Male' ? 'male' : 'female'}"></i> ${e.gender}
                    </span>
                </td>
                <td>${e.address}</td>
            </tr>`).join('');
    };

    window.getFormData = function () {
        return {
            empId: document.getElementById('empId').value.trim(),
            firstName: document.getElementById('firstName').value.trim(),
            lastName: document.getElementById('lastName').value.trim(),
            dob: document.getElementById('dob').value.trim(),
            gender: document.querySelector('input[name=gender]:checked').value,
            address: document.getElementById('address').value.trim(),
        };
    };

    window.selectRow = function (dbId) {
        selectedId = dbId;
        const emp = currentEmployees.find(e => e.dbId === dbId);
        if (!emp) return;
        document.getElementById('empId').value = emp.id;
        document.getElementById('firstName').value = emp.firstName;
        document.getElementById('lastName').value = emp.lastName;
        document.getElementById('dob').value = emp.dob;
        document.getElementById('address').value = emp.address;
        document.querySelectorAll('input[name=gender]').forEach(r => r.checked = r.value === emp.gender);
        renderTable();
    };

    window.clearForm = function () {
        ['empId', 'firstName', 'lastName', 'dob', 'address'].forEach(id => document.getElementById(id).value = '');
        document.querySelectorAll('input[name=gender]')[0].checked = true;
        selectedId = null;
        document.getElementById('avatarCircle').innerHTML = '<i class="ti ti-user"></i>';
        renderTable();
    };

    window.addEmployee = async function () {
        const d = getFormData();
        if (!d.empId || !d.firstName) { alert('Vui lòng nhập ID và First Name!'); return; }
        if (currentEmployees.find(e => e.id === d.empId)) { alert('ID đã tồn tại!'); return; }
        try {
            const res = await fetch('/api/users', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(d)});
            const result = await res.json();
            if(result.success) { fetchEmployees(); clearForm(); alert('Thêm thành công'); }
            else { alert('Lỗi khi thêm'); }
        } catch(e) { alert('Lỗi kết nối'); }
    };

    window.saveEmployee = async function () {
        if (!selectedId) { alert('Vui lòng chọn nhân viên cần lưu!'); return; }
        const d = getFormData();
        try {
            const res = await fetch('/api/users/' + selectedId, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(d)});
            const result = await res.json();
            if(result.success) { fetchEmployees(); clearForm(); alert('Đã lưu thành công'); }
            else { alert('Lỗi khi lưu'); }
        } catch(e) { alert('Lỗi kết nối'); }
    };

    window.editEmployee = function () {
        if (!selectedId) { alert('Vui lòng chọn nhân viên cần sửa!'); return; }
        document.getElementById('firstName').focus();
    };

    window.deleteEmployee = async function () {
        if (!selectedId) { alert('Vui lòng chọn nhân viên cần xóa!'); return; }
        if (!confirm('Xóa nhân viên này?')) return;
        try {
            const res = await fetch('/api/users/' + selectedId, {method: 'DELETE'});
            const result = await res.json();
            if(result.success) { fetchEmployees(); clearForm(); alert('Đã xóa thành công'); }
            else { alert('Lỗi khi xóa'); }
        } catch(e) { alert('Lỗi kết nối'); }
    };

    window.changeAvatar = function (event) {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = ev => {
            document.getElementById('avatarCircle').innerHTML =
                `<img src="${ev.target.result}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />`;
        };
        reader.readAsDataURL(file);
    };

    fetchEmployees();
});

// LOGOUT HANDLER
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[onclick*="login.html"], a[href*="login.html"]').forEach(el => {
        el.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            try { await fetch('/api/logout'); } catch(err) {}
            window.location.href = '/login';
        });
    });
});

// CHANGE PASSWORD HANDLER
document.addEventListener('DOMContentLoaded', () => {
    const cpForm = document.getElementById('changePasswordForm');
    if (cpForm) {
        cpForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const oldP = document.getElementById('oldPassword').value;
            const newP = document.getElementById('newPassword').value;
            const confP = document.getElementById('confirmPassword').value;
            if (newP !== confP) {
                alert('Mật khẩu mới không khớp!');
                return;
            }
            try {
                const res = await fetch('/api/change_password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({old_password: oldP, new_password: newP})
                });
                const data = await res.json();
                alert(data.message);
                if (data.success) {
                    window.location.href = '/dashboard';
                }
            } catch(err) { alert('Lỗi kết nối!'); }
        });
    }

    // Intercept "Đổi Mật Khẩu" link in sidebar
    document.querySelectorAll('span, a, li').forEach(el => {
        if (el.textContent && el.textContent.trim() === 'Đổi Mật Khẩu' && (el.tagName === 'SPAN' || el.tagName === 'A')) {
            const container = el.closest('li') || el;
            if (container) {
                container.style.cursor = 'pointer';
                container.addEventListener('click', (e) => {
                    e.preventDefault();
                    window.location.href = '/changepassword';
                });
            }
        }
    });
});

