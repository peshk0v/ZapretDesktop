let currentPage = 'home';
let zapretActive = false;
let currentObName = '';
let selectedObName = null;
let oblist = [];
let servicesList = [];
let servicesChanged = false;
let originalSettings = null;
let settingsChanged = false;
let sudoPassword = null;
let currentTheme = null;
let themeChanged = false;

function safeAddEventListener(id, event, handler) {
    const element = document.getElementById(id);
    if (element) {
        element.addEventListener(event, handler);
    } else {
        console.warn(`Элемент с id="${id}" не найден`);
    }
}

function showZapretLoading(message) {
    const overlay = document.getElementById('zapret-overlay');
    const text = document.getElementById('zapret-overlay-text');
    if (text) text.textContent = message;
    if (overlay) overlay.style.display = 'flex';
}

function hideZapretLoading() {
    const overlay = document.getElementById('zapret-overlay');
    if (overlay) overlay.style.display = 'none';
}

const GRADIENT_PRESETS = [
    { name: "Purple Dream", angle: 135, start: {r: 102, g: 126, b: 234}, end: {r: 118, g: 75, b: 162} },
    { name: "Ocean Blue", angle: 120, start: {r: 0, g: 119, b: 182}, end: {r: 0, g: 180, b: 216} },
    { name: "Forest", angle: 90, start: {r: 34, g: 139, b: 34}, end: {r: 60, g: 179, b: 113} },
    { name: "Sunset", angle: 45, start: {r: 255, g: 94, b: 77}, end: {r: 255, g: 159, b: 67} },
    { name: "Pink", angle: 150, start: {r: 238, g: 44, b: 130}, end: {r: 255, g: 105, b: 180} },
    { name: "Sunrise", angle: 30, start: {r: 255, g: 107, b: 107}, end: {r: 255, g: 159, b: 67} },
    { name: "Teal", angle: 160, start: {r: 0, g: 128, b: 128}, end: {r: 64, g: 224, b: 208} },
    { name: "Indigo", angle: 135, start: {r: 75, g: 0, b: 130}, end: {r: 123, g: 104, b: 238} },
    { name: "Sky", angle: 180, start: {r: 135, g: 206, b: 235}, end: {r: 176, g: 224, b: 230} },
    { name: "Coral", angle: 140, start: {r: 255, g: 127, b: 80}, end: {r: 255, g: 99, b: 71} },
    { name: "Lavender", angle: 120, start: {r: 181, g: 126, b: 220}, end: {r: 216, g: 191, b: 216} },
    { name: "Mint", angle: 110, start: {r: 189, g: 252, b: 201}, end: {r: 0, g: 250, b: 154} },
    { name: "Midnight", angle: 135, start: {r: 20, g: 20, b: 40}, end: {r: 60, g: 20, b: 100} },
    { name: "Fire", angle: 45, start: {r: 255, g: 69, b: 0}, end: {r: 255, g: 140, b: 0} },
    { name: "Ice", angle: 160, start: {r: 202, g: 228, b: 241}, end: {r: 173, g: 216, b: 230} },
    { name: "Aurora", angle: 135, start: {r: 0, g: 255, b: 127}, end: {r: 0, g: 191, b: 255} },
    { name: "Berry", angle: 140, start: {r: 128, g: 0, b: 128}, end: {r: 219, g: 112, b: 219} },
    { name: "Neon", angle: 90, start: {r: 0, g: 255, b: 255}, end: {r: 255, g: 0, b: 255} },
    { name: "Autumn", angle: 30, start: {r: 205, g: 133, b: 63}, end: {r: 244, g: 164, b: 96} },
    { name: "Galaxy", angle: 135, start: {r: 25, g: 25, b: 112}, end: {r: 138, g: 43, b: 226} },
    { name: "Ocean Deep", angle: 180, start: {r: 0, g: 105, b: 148}, end: {r: 72, g: 209, b: 204} },
    { name: "Sunflower", angle: 45, start: {r: 255, g: 223, b: 0}, end: {r: 255, g: 165, b: 0} },
    { name: "Rose Gold", angle: 120, start: {r: 183, g: 65, b: 98}, end: {r: 255, g: 182, b: 193} },
    { name: "Emerald", angle: 150, start: {r: 0, g: 100, b: 0}, end: {r: 144, g: 238, b: 144} }
];

let logs = [];

const logModes = {
    0: { class: 'info', title: 'Информация' },
    1: { class: 'warning', title: 'Предупреждение' },
    2: { class: 'error', title: 'Ошибка' }
};

window.addLog = function(text, mode) {
    logs.push({ text, mode, timestamp: Date.now() });
    
    if (logs.length > 50) {
        logs = logs.slice(-50);
    }
    
    renderLogs();
};

function renderLogs() {
    const container = document.getElementById('logs-list');
    if (!container) return;
    
    const displayLogs = logs.slice(-10);
    
    container.innerHTML = displayLogs.map(log => {
        const info = logModes[log.mode] || logModes[0];
        return `
            <div class="log-message ${info.class}">
                <div class="log-indicator"></div>
                <div class="log-content">
                    <div class="log-title">${info.title}</div>
                    <div class="log-text">${escapeHtml(log.text)}</div>
                </div>
            </div>
        `;
    }).join('');
    
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function clearLogs() {
    logs = [];
    renderLogs();
}

async function switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    document.getElementById(`${page}-page`).classList.add('active');
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
    currentPage = page;

    if (page === 'bypasses') {
        await loadBypasses();
    } else if (page === 'home') {
        await updateUI();
    } else if (page === 'services') {
        await loadServices();
    } else if (page === 'settings') {
        await loadSettings();
    }
}

async function loadAutostartStatus() {
    try {
        const status = await eel.get_autostart_status()();
        const checkbox = document.getElementById('autostart-checkbox');
        if (checkbox) {
            checkbox.checked = status;
        }
    } catch (error) {
        console.error('Ошибка загрузки статуса автозапуска:', error);
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
        toggleBtn.classList.add('stopped');
        statusText.textContent = 'Статус: Работает';
    } else {
        toggleBtn.textContent = 'Активировать';
        toggleBtn.classList.remove('stopped');
        statusText.textContent = 'Статус: Остановлен';
    }

    await loadAutostartStatus();
}

function hslToRgb(h, s, l) {
  h /= 360; s /= 100; l /= 100;
  let r, g, b;
  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  return {
    r: Math.round(r * 255),
    g: Math.round(g * 255),
    b: Math.round(b * 255)
  };
}

function randomColorFromHue(hue) {
  return hslToRgb(hue, 70, 60);
}

function setRandomGradient() {
  const hue1 = Math.floor(Math.random() * 360);
  const hue2 = (hue1 + 30 + Math.floor(Math.random() * 60)) % 360;
  const color1 = randomColorFromHue(hue1);
  const color2 = randomColorFromHue(hue2);
  const angle = Math.floor(Math.random() * 360);

  const root = document.documentElement;
  root.style.setProperty('--gradient-angle', angle + 'deg');
  root.style.setProperty('--gradient-start-r', color1.r);
  root.style.setProperty('--gradient-start-g', color1.g);
  root.style.setProperty('--gradient-start-b', color1.b);
  root.style.setProperty('--gradient-end-r', color2.r);
  root.style.setProperty('--gradient-end-g', color2.g);
  root.style.setProperty('--gradient-end-b', color2.b);

  return { angle, start: color1, end: color2 };
}

function applyTheme(theme) {
  const root = document.documentElement;
  root.style.setProperty('--gradient-angle', theme.angle + 'deg');
  root.style.setProperty('--gradient-start-r', theme.start.r);
  root.style.setProperty('--gradient-start-g', theme.start.g);
  root.style.setProperty('--gradient-start-b', theme.start.b);
  root.style.setProperty('--gradient-end-r', theme.end.r);
  root.style.setProperty('--gradient-end-g', theme.end.g);
  root.style.setProperty('--gradient-end-b', theme.end.b);
}

async function loadTheme() {
  try {
    currentTheme = await eel.get_theme()();
    applyTheme(currentTheme);
  } catch (error) {
    console.error('Ошибка загрузки темы:', error);
  }
}

async function saveCurrentTheme() {
  if (!currentTheme) return;
  try {
    await eel.save_theme(currentTheme)();
    themeChanged = false;
  } catch (error) {
    console.error('Ошибка сохранения темы:', error);
  }
}

function renderPresets() {
  const grid = document.getElementById('preset-grid');
  if (!grid) return;
  grid.innerHTML = '';

  GRADIENT_PRESETS.forEach((preset, index) => {
    const card = document.createElement('div');
    card.className = 'preset-card';
    card.dataset.preset = preset.name;

    const preview = document.createElement('div');
    preview.className = 'preset-preview';
    preview.style.background = `linear-gradient(${preset.angle}deg, 
      rgb(${preset.start.r}, ${preset.start.g}, ${preset.start.b}), 
      rgb(${preset.end.r}, ${preset.end.g}, ${preset.end.b}))`;

    const name = document.createElement('div');
    name.className = 'preset-name';
    name.textContent = preset.name;

    card.appendChild(preview);
    card.appendChild(name);

    if (currentTheme && currentTheme.preset === preset.name) {
      card.classList.add('selected');
    }

    card.addEventListener('click', async () => {
      document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');

      currentTheme = {
        angle: preset.angle,
        start: preset.start,
        end: preset.end,
        preset: preset.name
      };
      applyTheme(currentTheme);
      themeChanged = true;
      await saveCurrentTheme();
    });

    grid.appendChild(card);
  });
}

function initSettingsTabs() {
  document.querySelectorAll('.settings-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.settings-tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.tab + '-tab').classList.add('active');

      if (tab.dataset.tab === 'desktop') {
        renderPresets();
      }
    });
  });
}

async function handleToggle() {
    const toggleBtn = document.getElementById('toggle-btn');
    toggleBtn.disabled = true;

    showZapretLoading(zapretActive ? 'Отключение...' : 'Подключение...');

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
        hideZapretLoading();
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

async function loadSettings() {
    try {
        originalSettings = await eel.getsets()();
        console.log('getsets() returned:', originalSettings);

        document.querySelectorAll('input[name="ipset"]').forEach(radio => {
            if (radio.value === originalSettings.IPSET) {
                radio.checked = true;
            }
        });

        document.getElementById('gamefilter-switch').checked = originalSettings.GameFilter;
        document.getElementById('auto-update-services-switch').checked = originalSettings.autoUpdateServices || false;
        document.getElementById('auto-update-zapret-switch').checked = originalSettings.autoUpdateZapret || false;

        document.getElementById('settings-save-btn-container').style.display = 'none';
        settingsChanged = false;
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
    }
}

function checkSettingsChanged() {
    if (!originalSettings) {
        console.log('checkSettingsChanged: originalSettings ещё не загружены');
        return false;
    }

    const currentIPSet = document.querySelector('input[name="ipset"]:checked')?.value;
    const currentGameFilter = document.getElementById('gamefilter-switch').checked;
    const currentAutoUpdateServices = document.getElementById('auto-update-services-switch').checked;
    const currentAutoUpdateZapret = document.getElementById('auto-update-zapret-switch').checked;

    const changed = (currentIPSet !== originalSettings.IPSET) ||
                    (currentGameFilter !== originalSettings.GameFilter) ||
                    (currentAutoUpdateServices !== (originalSettings.autoUpdateServices || false)) ||
                    (currentAutoUpdateZapret !== (originalSettings.autoUpdateZapret || false));

    if (changed !== settingsChanged) {
        settingsChanged = changed;
        document.getElementById('settings-save-btn-container').style.display = changed ? 'block' : 'none';
    }
}

async function saveSettings() {
    const currentIPSet = document.querySelector('input[name="ipset"]:checked')?.value;
    const currentGameFilter = document.getElementById('gamefilter-switch').checked;

    if (!currentIPSet) {
        console.warn('IPSet Filter не выбран');
        return;
    }

    const updatedSettings = {
        IPSET: currentIPSet,
        GameFilter: currentGameFilter,
        autoUpdateServices: document.getElementById('auto-update-services-switch').checked,
        autoUpdateZapret: document.getElementById('auto-update-zapret-switch').checked
    };

    const saveBtn = document.getElementById('save-settings-btn');
    saveBtn.disabled = true;

    showZapretLoading('Сохранение настроек...');

    try {
        await eel.savesets(updatedSettings)();
        originalSettings = updatedSettings;
        settingsChanged = false;
        document.getElementById('settings-save-btn-container').style.display = 'none';
    } catch (error) {
        console.error('Ошибка сохранения настроек:', error);
    } finally {
        saveBtn.disabled = false;
        hideZapretLoading();
    }
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

    showZapretLoading('Сохранение обхода...');

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
        hideZapretLoading();
    }
}

async function loadServices() {
    servicesList = await eel.getservc()();
    servicesChanged = false;
    document.getElementById('save-services-btn').classList.remove('visible');
    renderServicesList(servicesList);
}

function renderServicesList(services) {
    const container = document.getElementById('services-list');
    container.innerHTML = '';

    services.forEach((service) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'service-wrapper';

        // Карточка
        const card = document.createElement('div');
        card.className = 'service-card';

        // Иконка
        const iconDiv = document.createElement('div');
        iconDiv.className = 'service-icon';
        if (service.Icon) {
            iconDiv.style.backgroundImage = `url('${service.Icon}')`;
        } else {
            iconDiv.style.backgroundColor = '#4a3aff';
            iconDiv.textContent = service.Name.charAt(0).toUpperCase();
        }

        // Название
        const nameSpan = document.createElement('span');
        nameSpan.className = 'service-name';
        nameSpan.textContent = service.Name;

        // Тумблер
        const switchLabel = document.createElement('label');
        switchLabel.className = 'switch';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = service.Enabled;
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            if (!servicesChanged) {
                servicesChanged = true;
                document.getElementById('save-services-btn').classList.add('visible');
            }
        });
        const slider = document.createElement('span');
        slider.className = 'slider';
        switchLabel.appendChild(checkbox);
        switchLabel.appendChild(slider);

        const arrowSpan = document.createElement('span');
        arrowSpan.className = 'service-arrow';
        arrowSpan.textContent = '\uf0ab';

        card.appendChild(iconDiv);
        card.appendChild(nameSpan);
        card.appendChild(arrowSpan);
        card.appendChild(switchLabel);

        const ipsContainer = document.createElement('div');
        ipsContainer.className = 'service-ips';
        if (service.IPS && service.IPS.length > 0) {
            service.IPS.forEach(ip => {
                const ipItem = document.createElement('div');
                ipItem.className = 'ip-item';
                ipItem.textContent = ip;
                ipsContainer.appendChild(ipItem);
            });
        }

        wrapper.appendChild(card);
        wrapper.appendChild(ipsContainer);

        card.addEventListener('click', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.closest('.switch')) {
                return;
            }
            toggleIPList(wrapper);
        });

        container.appendChild(wrapper);
    });
}

function toggleIPList(wrapper) {
    const ipsContainer = wrapper.querySelector('.service-ips');
    if (!ipsContainer) return;

    if (ipsContainer.classList.contains('expanded')) {
        ipsContainer.classList.remove('expanded');
        ipsContainer.style.maxHeight = '0';
        ipsContainer.style.marginTop = '0';
    } else {
        ipsContainer.classList.add('expanded');
        ipsContainer.style.maxHeight = '0';
        ipsContainer.style.marginTop = '0';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                const scrollHeight = ipsContainer.scrollHeight;
                ipsContainer.style.maxHeight = scrollHeight + 'px';
                ipsContainer.style.marginTop = '-10px';
            });
        });
    }

    const arrow = wrapper.querySelector('.service-card .service-arrow');
    if (arrow) {
        arrow.textContent = ipsContainer.classList.contains('expanded') ? '\uf0aa' : '\uf0ab';
    }
}

async function loadSavedPassword() {
    try {
        const saved = await eel.get_saved_password()();
        if (saved) {
            sudoPassword = saved;
            await eel.set_sudo_password(saved);
        }
    } catch (e) { console.error('Ошибка загрузки пароля:', e); }
}

async function checkPassword() {
    const saved = await eel.get_saved_password()();
    if (!saved) {
        await show_password_modal();
    }
}

eel.expose(show_password_modal);
async function show_password_modal() {
    return new Promise((resolve) => {
        const modal = document.getElementById('password-modal');
        const input = document.getElementById('sudo-password-input');
        const submitBtn = document.getElementById('sudo-password-submit');
        const errorDiv = document.getElementById('sudo-password-error') || (() => {
            const div = document.createElement('div');
            div.id = 'sudo-password-error';
            div.style.color = '#ff3b30';
            div.style.marginTop = '10px';
            div.style.fontSize = '0.9rem';
            modal.querySelector('.password-modal-content').appendChild(div);
            return div;
        })();

        modal.classList.add('visible');
        input.value = '';
        input.focus();
        errorDiv.textContent = '';

        const onSubmit = async () => {
            const password = input.value.trim();
            if (!password) return;

            await eel.save_sudo_password(password)();
            await eel.set_sudo_password(password);

            const ok = await eel.test_sudo()();
            if (ok) {
                modal.classList.remove('visible');
                resolve(password);
            } else {
                errorDiv.textContent = 'Неверный пароль sudo. Попробуйте ещё раз.';
                input.value = '';
                input.focus();
                await eel.save_sudo_password('');
            }
        };

        const onKeyPress = (e) => {
            if (e.key === 'Enter') onSubmit();
        };

        input.addEventListener('keypress', onKeyPress);
        submitBtn.addEventListener('click', onSubmit);
    });
}
window.show_password_modal = show_password_modal;

async function saveServices() {
    const checkboxes = document.querySelectorAll('#services-list .service-card input[type="checkbox"]');
    const enabledStates = Array.from(checkboxes).map(cb => cb.checked);

    showZapretLoading('Сохранение сервисов...');

    try {
        await eel.setservc(enabledStates)();
        servicesChanged = false;
        document.getElementById('save-services-btn').classList.remove('visible');
        await loadServices();
    } catch (error) {
        console.error('Ошибка сохранения сервисов:', error);
    } finally {
        hideZapretLoading();
    }
}

async function handleAutostart(e) {
    const enabled = e.target.checked;
    await eel.astrt(enabled)();
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTheme();
  initSettingsTabs();

  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      await switchPage(btn.dataset.page);
    });
  });

  safeAddEventListener('refresh-services-btn', 'click', async () => {
    console.log('Обновление списка сервисов: клик');
    showZapretLoading('Обновление списка сервисов...');

    try {
      await eel.updServc()();
      await loadServices();
      console.log('Обновление списка сервисов: успешно');
    } catch (error) {
      console.error('Ошибка обновления:', error);
    } finally {
      hideZapretLoading();
    }
  });

  document.querySelectorAll('#settings-page input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', checkSettingsChanged);
  });

  await updateUI();
  await checkPassword();

  await loadSettings();

  if (originalSettings?.autoUpdateServices) {
    showZapretLoading('Обновление списка сервисов...');
    try {
      await eel.updServc()();
      await loadServices();
    } catch (error) {
      console.error('Ошибка автообновления:', error);
    } finally {
      hideZapretLoading();
    }
  }

  safeAddEventListener('gamefilter-switch', 'change', checkSettingsChanged);
  safeAddEventListener('auto-update-services-switch', 'change', checkSettingsChanged);
  safeAddEventListener('auto-update-zapret-switch', 'change', checkSettingsChanged);
  safeAddEventListener('save-settings-btn', 'click', saveSettings);
  safeAddEventListener('save-services-btn', 'click', saveServices);

  safeAddEventListener('clear-logs-btn', 'click', clearLogs);

  safeAddEventListener('toggle-btn', 'click', handleToggle);
  safeAddEventListener('save-bypass-btn', 'click', saveBypass);

  safeAddEventListener('update-zapret-btn', 'click', async () => {
    console.log('Обновление zapret: клик');
    showZapretLoading('Обновление zapret...');
    try {
      await eel.update_zapret()();
      console.log('Обновление zapret: успешно');
    } catch (error) {
      console.error('Ошибка обновления:', error);
    } finally {
      hideZapretLoading();
    }
  });

  safeAddEventListener('random-gradient-btn', 'click', async () => {
    console.log('Рандомный градиент: клик');
    const hue1 = Math.floor(Math.random() * 360);
    const hue2 = (hue1 + 30 + Math.floor(Math.random() * 60)) % 360;
    const color1 = randomColorFromHue(hue1);
    const color2 = randomColorFromHue(hue2);
    const angle = Math.floor(Math.random() * 360);

    console.log('Рандомный градиент: hue1=' + hue1 + ', hue2=' + hue2 + ', angle=' + angle);
    console.log('Рандомный градиент: color1=' + JSON.stringify(color1) + ', color2=' + JSON.stringify(color2));

    currentTheme = {
      angle: angle,
      start: color1,
      end: color2,
      preset: null
    };

    console.log('Рандомный градиент: currentTheme=' + JSON.stringify(currentTheme));

    applyTheme(currentTheme);
    console.log('Рандомный градиент: applyTheme выполнен');

    try {
      await saveCurrentTheme();
      console.log('Рандомный градиент: сохранено');
    } catch (error) {
      console.error('Рандомный градиент: ошибка сохранения', error);
    }

    renderPresets();
    console.log('Рандомный градиент: пресеты отрисованы');
  });
});
