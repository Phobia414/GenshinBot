const tg = window.Telegram?.WebApp;
let userData = null;

// Инициализация Telegram
if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor('#060e0d');
    tg.setBackgroundColor('#060e0d');

    // Загружаем данные профиля с сервера
    fetch(`/api/profile?init_data=${encodeURIComponent(tg.initData)}`)
        .then(res => res.json())
        .then(data => {
            if (data && !data.detail) {
                userData = data;
                document.getElementById('profile-name').innerText = data.name;
                document.getElementById('profile-balance').innerText = data.balance.toLocaleString() + " 💰";
                document.getElementById('profile-rep').innerText = data.reputation + " 🎖️";
                document.getElementById('profile-avatar').innerText = data.name.charAt(0).toUpperCase();
                document.getElementById('top-avatar').innerText = data.name.charAt(0).toUpperCase();
                document.getElementById('profile-status').innerText = data.is_admin ? "Ранг: Администратор" : "Ранг: Игрок";

                // Если пользователь админ, показываем вкладку
                if (data.is_admin) {
                    document.getElementById('nav-admin').style.display = 'flex';
                    loadAdminApps();
                }
            }
        })
        .catch(err => console.error("Ошибка загрузки профиля:", err));
}

// Переключение вкладок
const navItems = document.querySelectorAll('.nav-item');
const screens = document.querySelectorAll('.screen');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        if (tg) tg.HapticFeedback.impactOccurred('light'); // Вибрация

        navItems.forEach(nav => nav.classList.remove('active'));
        screens.forEach(screen => screen.classList.remove('active'));

        item.classList.add('active');
        document.getElementById(item.getAttribute('data-target')).classList.add('active');
    });
});

// ===== ИСПРАВЛЕНИЕ: обработчик для кнопки "Создать героя" =====
document.getElementById('btn-open-sheet').addEventListener('click', () => {
    openSheet('reg-sheet');
});

// Управление шторкой
function openSheet(id) {
    if (tg) tg.HapticFeedback.impactOccurred('medium');
    document.getElementById(id).classList.add('active');
    document.getElementById('sheet-overlay').classList.add('active');
}

function closeSheet() {
    document.getElementById('reg-sheet').classList.remove('active');
    document.getElementById('sheet-overlay').classList.remove('active');
}

// Отправка анкеты
async function submitApplication() {
    if (!tg) return alert("Доступно только в Telegram");

    const age = document.getElementById('form-age').value;
    if (!age || isNaN(age)) {
        return tg.showAlert("Пожалуйста, введите корректный возраст цифрой.");
    }

    const payload = {
        initData: tg.initData,
        age: age,
        experience: document.getElementById('form-exp').value || "Не указан",
        about: document.getElementById('form-about').value || "Не указано",
        timezone: document.getElementById('form-tz').value || "Не указан",
        source: document.getElementById('form-source').value || "Не указан",
        activity: document.getElementById('form-activity').value || "Не указана"
    };

    try {
        const res = await fetch('/api/apply', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        tg.showAlert(result.message || "Анкета отправлена!");
        closeSheet();
    } catch(e) {
        tg.showAlert("Ошибка сети. Попробуйте позже.");
    }
}

// Покупка в магазине
async function buyItem(item, price) {
    if (!tg) return alert("Доступно только в Telegram");

    const res = await fetch('/api/buy', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({initData: tg.initData, item: item})
    });
    const result = await res.json();
    tg.showAlert(result.message);

    // Обновляем баланс на экране
    if (result.status === "ok" && userData) {
        tg.HapticFeedback.notificationOccurred('success');
        userData.balance -= price;
        document.getElementById('profile-balance').innerText = userData.balance.toLocaleString() + " 💰";
    } else {
        tg.HapticFeedback.notificationOccurred('error');
    }
}

// Загрузка анкет для админа
async function loadAdminApps() {
    if (!tg) return;
    const res = await fetch(`/api/admin/apps?init_data=${encodeURIComponent(tg.initData)}`);
    const data = await res.json();

    const container = document.getElementById('admin-apps-list');
    container.innerHTML = "";

    if (!data.apps || data.apps.length === 0) {
        container.innerHTML = "<p class='loading-text'>Новых анкет нет.</p>";
        return;
    }

    data.apps.forEach(app => {
        container.innerHTML += `
            <div class="admin-card">
                <h3>ID Пользователя: ${app.user_id}</h3>
                <p><b>Возраст:</b> ${app.age}</p>
                <p><b>Опыт:</b> ${app.experience.substring(0, 50)}...</p>
                <p><b>Источник:</b> ${app.source}</p>
                <button class="buy-btn" style="background:var(--accent);color:black;width:100%;margin-top:10px;" onclick="alert('Одобрение из Mini App в разработке. Используйте бота.')">Рассмотреть</button>
            </div>
        `;
    });
}

// Обработка кнопки "Вход в группу"
document.getElementById('btn-join-group').addEventListener('click', () => {
    if (tg) {
        tg.openTelegramLink("https://t.me/your_group_link_here"); // Замени на ссылку группы
    }
});