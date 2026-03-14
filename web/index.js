let currentPage = 'home';
let zapretActive = false;
let currentObName = '';
let selectedObName = null;
let oblist = [];

function switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    document.getElementById(`${page}-page`).classList.add('active');
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
    currentPage = page;

    if (page === 'bypasses') {
        loadBypasses();
    } else if (page === 'home') {
        updateUI();
    }
}

async function updateUI() {
    const obname = await eel.get_obname()();
    document.getElementById('obname-value').textContent = obname;

    const status = await eel.get_status()();
    zapretActive = status;

    const toggleBtn = document.getElementById('toggle-btn');
    const statusText = document.getElementById('status-text');

    if (status) {
        toggleBtn.textContent = 'Остановить';
        toggleBtn.classList.add('stopped');   // красный для "Остановить"
        statusText.textContent = 'Статус: Работает';
    } else {
        toggleBtn.textContent = 'Активировать';
        toggleBtn.classList.remove('stopped'); // синий для "Активировать"
        statusText.textContent = 'Статус: Остановлен';
    }
}

async function handleToggle() {
    const toggleBtn = document.getElementById('toggle-btn');
    toggleBtn.disabled = true;

    try {
        if (zapretActive) {
            await eel.stop_zapret()();
        } else {
            await eel.start_zapret()();
        }
        await updateUI();
    } catch (error) {
        console.error('Ошибка:', error);
    } finally {
        toggleBtn.disabled = false;
    }
}

async function loadBypasses() {
    currentObName = await eel.get_obname()();
    oblist = await eel.get_oblist()();

    document.getElementById('current-obname').textContent = currentObName;
    selectedObName = null;
    document.getElementById('save-button-container').style.display = 'none';

    renderBypassList();
}

function renderBypassList() {
    const listContainer = document.getElementById('bypasses-list');
    listContainer.innerHTML = '';

    oblist.forEach(name => {
        const card = document.createElement('div');
        card.className = 'bypass-card';
        if (name === currentObName) {
            card.classList.add('current');
        }
        card.textContent = name;
        card.dataset.name = name;

        card.addEventListener('click', () => {
            if (name === currentObName) return;
            document.querySelectorAll('.bypass-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedObName = name;
            document.getElementById('save-button-container').style.display = 'block';
        });

        listContainer.appendChild(card);
    });
}

async function saveBypass() {
    if (!selectedObName) return;
    const saveBtn = document.getElementById('save-bypass-btn');
    saveBtn.disabled = true;
    try {
        await eel.set_obname(selectedObName)();
        currentObName = selectedObName;
        document.getElementById('current-obname').textContent = currentObName;
        renderBypassList();
        document.getElementById('save-button-container').style.display = 'none';
        selectedObName = null;

        if (currentPage === 'home') {
            updateUI();
        }
    } catch (error) {
        console.error('Ошибка сохранения:', error);
    } finally {
        saveBtn.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchPage(btn.dataset.page);
        });
    });

    await updateUI();

    document.getElementById('toggle-btn').addEventListener('click', handleToggle);
    document.getElementById('autostart-checkbox').addEventListener('change', handleAutostart);
    document.getElementById('save-bypass-btn').addEventListener('click', saveBypass);
});