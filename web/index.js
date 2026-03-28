let currentPage = 'home';
let zapretActive = false;
let currentObName = '';
let selectedObName = null;
let oblist = [];
let servicesList = [];
let servicesChanged = false;
let originalSettings = null;
let settingsChanged = false;
let currentTheme = null;
let themeChanged = false;
let backgroundList = [];
let backgroundsChanged = false;
let currentBackgroundType = 'gradient';
let editingBackgroundIndex = null;

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

    const autostartCheckbox = document.getElementById('autostart-checkbox');
    if (autostartCheckbox) {
        try {
            const autostart = await eel.get_autostart_status()();
            autostartCheckbox.checked = autostart;
        } catch (e) {
            console.error('Ошибка загрузки автозапуска:', e);
        }
    }
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

async function loadTheme() {
  try {
    currentTheme = await eel.get_theme()();
    if (!currentTheme) {
      currentTheme = {
        angle: 135,
        start: {r: 102, g: 126, b: 234},
        end: {r: 118, g: 75, b: 162},
        preset: 'Purple Dream',
        type: 'gradient'
      };
    }
    if (!currentTheme.type) {
      currentTheme.type = 'gradient';
    }
    if (currentTheme.type === 'image') {
      currentBackgroundType = 'image';
      document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
      document.querySelector('.type-btn[data-type="image"]').classList.add('active');
      document.getElementById('gradient-section').style.display = 'none';
      document.getElementById('image-section').style.display = 'block';
    }
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

  GRADIENT_PRESETS.forEach((preset) => {
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

    if (currentTheme && currentTheme.preset === preset.name && currentBackgroundType === 'gradient') {
      card.classList.add('selected');
    }

    card.addEventListener('click', async () => {
      document.querySelectorAll('#preset-grid .preset-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');

      currentTheme = {
        angle: preset.angle,
        start: preset.start,
        end: preset.end,
        preset: preset.name,
        type: 'gradient'
      };
      applyTheme(currentTheme);
      themeChanged = true;
      await saveCurrentTheme();
    });

    grid.appendChild(card);
  });
}

async function loadBackgrounds() {
  try {
    backgroundList = await eel.get_backgrounds()();
    renderBackgroundCards();
  } catch (error) {
    console.error('Ошибка загрузки обоев:', error);
  }
}

function renderBackgroundCards() {
  const grid = document.getElementById('background-grid');
  if (!grid) return;
  grid.innerHTML = '';

  backgroundList.forEach((bg, index) => {
    const card = document.createElement('div');
    card.className = 'preset-card';
    card.dataset.index = index;

    const preview = document.createElement('div');
    preview.className = 'preset-preview';
    preview.style.backgroundImage = `url('style/content/backgrounds/${bg.File}')`;
    preview.style.backgroundSize = 'cover';
    preview.style.backgroundPosition = 'center';

    const colorBtn = document.createElement('button');
    colorBtn.className = 'color-edit-btn';
    colorBtn.innerHTML = '&#xf044;';
    colorBtn.title = 'Изменить цвет';
    colorBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openEditColorModal(index);
    });

    const name = document.createElement('div');
    name.className = 'preset-name';
    name.textContent = bg.Name;

    card.appendChild(preview);
    card.appendChild(colorBtn);
    card.appendChild(name);

    if (currentTheme && currentTheme.type === 'image' && currentTheme.imageFile === bg.File) {
      card.classList.add('selected');
    }

    const color = bg.Color || [255, 107, 107];
    card.style.boxShadow = `0 4px 15px rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.4)`;

    card.addEventListener('click', async () => {
      document.querySelectorAll('#background-grid .preset-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');

      currentTheme = {
        type: 'image',
        imageFile: bg.File,
        color: bg.Color
      };
      applyImageTheme(bg.File, bg.Color);
      themeChanged = true;
      await saveCurrentTheme();
    });

    grid.appendChild(card);
  });
}

function applyImageTheme(imageFile, color) {
  const root = document.documentElement;
  document.body.style.background = `url('style/content/backgrounds/${imageFile}')`;
  document.body.style.backgroundSize = 'cover';
  document.body.style.backgroundPosition = 'center';
  
  if (color) {
    root.style.setProperty('--gradient-start-r', color[0]);
    root.style.setProperty('--gradient-start-g', color[1]);
    root.style.setProperty('--gradient-start-b', color[2]);
    root.style.setProperty('--gradient-end-r', color[0]);
    root.style.setProperty('--gradient-end-g', color[1]);
    root.style.setProperty('--gradient-end-b', color[2]);
  }
}

function applyTheme(theme) {
  if (theme.type === 'image') {
    applyImageTheme(theme.imageFile, theme.color);
    return;
  }
  
  const root = document.documentElement;
  document.body.style.background = '';
  root.style.setProperty('--gradient-angle', theme.angle + 'deg');
  root.style.setProperty('--gradient-start-r', theme.start.r);
  root.style.setProperty('--gradient-start-g', theme.start.g);
  root.style.setProperty('--gradient-start-b', theme.start.b);
  root.style.setProperty('--gradient-end-r', theme.end.r);
  root.style.setProperty('--gradient-end-g', theme.end.g);
  root.style.setProperty('--gradient-end-b', theme.end.b);
}

function initBackgroundTypeToggle() {
  document.querySelectorAll('.type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      currentBackgroundType = btn.dataset.type;
      
      if (currentBackgroundType === 'gradient') {
        document.getElementById('gradient-section').style.display = 'block';
        document.getElementById('image-section').style.display = 'none';
        
        if (currentTheme && currentTheme.type !== 'gradient') {
          currentTheme = {
            angle: 135,
            start: {r: 102, g: 126, b: 234},
            end: {r: 118, g: 75, b: 162},
            preset: 'Purple Dream',
            type: 'gradient'
          };
          applyTheme(currentTheme);
          saveCurrentTheme();
        } else if (currentTheme && currentTheme.type === 'gradient') {
          applyTheme(currentTheme);
        }
      } else {
        document.getElementById('gradient-section').style.display = 'none';
        document.getElementById('image-section').style.display = 'block';
        loadBackgrounds();
      }
    });
  });
}

function openAddBackgroundModal() {
  document.getElementById('add-background-modal').style.display = 'flex';
  document.getElementById('bg-filename').value = '';
  document.getElementById('bg-name').value = '';
  document.getElementById('bg-color').value = '#ff6b6b';
}

function closeAddBackgroundModal() {
  document.getElementById('add-background-modal').style.display = 'none';
}

function openEditColorModal(index) {
  editingBackgroundIndex = index;
  const bg = backgroundList[index];
  const color = bg.Color || [255, 107, 107];
  const hexColor = '#' + color.map(c => c.toString(16).padStart(2, '0')).join('');
  document.getElementById('edit-bg-color').value = hexColor;
  document.getElementById('edit-color-modal').style.display = 'flex';
}

function closeEditColorModal() {
  document.getElementById('edit-color-modal').style.display = 'none';
  editingBackgroundIndex = null;
}

async function saveNewBackground() {
  const filename = document.getElementById('bg-filename').value;
  const name = document.getElementById('bg-name').value;
  const colorHex = document.getElementById('bg-color').value;
  
  if (!filename || !name) {
    alert('Пожалуйста, выберите файл и введите название');
    return;
  }
  
  const color = [
    parseInt(colorHex.slice(1, 3), 16),
    parseInt(colorHex.slice(3, 5), 16),
    parseInt(colorHex.slice(5, 7), 16)
  ];
  
  try {
    await eel.add_background(filename, name, color)();
    closeAddBackgroundModal();
    await loadBackgrounds();
  } catch (error) {
    console.error('Ошибка сохранения обоев:', error);
    alert('Ошибка при сохранении обоев');
  }
}

async function saveEditedColor() {
  if (editingBackgroundIndex === null) return;
  
  const colorHex = document.getElementById('edit-bg-color').value;
  const color = [
    parseInt(colorHex.slice(1, 3), 16),
    parseInt(colorHex.slice(3, 5), 16),
    parseInt(colorHex.slice(5, 7), 16)
  ];
  
  try {
    await eel.edit_background_color(editingBackgroundIndex, color)();
    closeEditColorModal();
    await loadBackgrounds();
    
    if (currentTheme && currentTheme.type === 'image') {
      const bg = backgroundList[editingBackgroundIndex];
      if (bg) {
        currentTheme.color = bg.Color;
        applyImageTheme(currentTheme.imageFile, bg.Color);
      }
    }
  } catch (error) {
    console.error('Ошибка изменения цвета:', error);
  }
}

async function selectBackgroundFile() {
  try {
    const result = await eel.select_background_file()();
    if (result) {
      document.getElementById('bg-filename').value = result;
    }
  } catch (error) {
    console.error('Ошибка выбора файла:', error);
  }
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
        initBackgroundTypeToggle();
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

        document.querySelectorAll('input[name="ipset"]').forEach(radio => {
            if (radio.value === originalSettings.IPSET) {
                radio.checked = true;
            }
        });

        document.querySelectorAll('input[name="gamefilter"]').forEach(radio => {
            if (radio.value === originalSettings.GameFilter) {
                radio.checked = true;
            }
        });

        const autoUpdateServicesSwitch = document.getElementById('auto-update-services-switch');
        const autoUpdateZapretSwitch = document.getElementById('auto-update-zapret-switch');
        if (autoUpdateServicesSwitch) {
            autoUpdateServicesSwitch.checked = originalSettings.autoUpdateServices || false;
        }
        if (autoUpdateZapretSwitch) {
            autoUpdateZapretSwitch.checked = originalSettings.autoUpdateZapret || false;
        }

        document.getElementById('settings-save-btn-container').style.display = 'none';
        settingsChanged = false;
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
    }
}

function checkSettingsChanged() {
    if (!originalSettings) {
        return false;
    }

    const currentIPSet = document.querySelector('input[name="ipset"]:checked')?.value;
    const currentGameFilter = document.querySelector('input[name="gamefilter"]:checked')?.value;
    const currentAutoUpdateServices = document.getElementById('auto-update-services-switch')?.checked || false;
    const currentAutoUpdateZapret = document.getElementById('auto-update-zapret-switch')?.checked || false;

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
    const currentGameFilter = document.querySelector('input[name="gamefilter"]:checked')?.value;

    if (!currentIPSet || !currentGameFilter) {
        console.warn('Не все параметры выбраны');
        return;
    }

    const updatedSettings = {
        IPSET: currentIPSet,
        GameFilter: currentGameFilter,
        autoUpdateServices: document.getElementById('auto-update-services-switch')?.checked || false,
        autoUpdateZapret: document.getElementById('auto-update-zapret-switch')?.checked || false
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
    document.getElementById('services-save-button-container').style.display = 'none';
    renderServicesList(servicesList);
}

function renderServicesList(services) {
    const container = document.getElementById('services-list');
    container.innerHTML = '';

    services.forEach((service) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'service-wrapper';

        const card = document.createElement('div');
        card.className = 'service-card';

        const iconDiv = document.createElement('div');
        iconDiv.className = 'service-icon';
        if (service.Icon) {
            iconDiv.style.backgroundImage = `url('${service.Icon}')`;
        } else {
            iconDiv.style.backgroundColor = '#4a3aff';
            iconDiv.textContent = service.Name.charAt(0).toUpperCase();
        }

        const nameSpan = document.createElement('span');
        nameSpan.className = 'service-name';
        nameSpan.textContent = service.Name;

        const switchLabel = document.createElement('label');
        switchLabel.className = 'switch';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = service.Enabled;
        checkbox.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!servicesChanged) {
                servicesChanged = true;
                document.getElementById('services-save-button-container').style.display = 'block';
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

async function saveServices() {
    const checkboxes = document.querySelectorAll('#services-list .service-card input[type="checkbox"]');
    const enabledStates = Array.from(checkboxes).map(cb => cb.checked);

    showZapretLoading('Сохранение сервисов...');

    try {
        await eel.setservc(enabledStates)();
        servicesChanged = false;
        document.getElementById('services-save-button-container').style.display = 'none';
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
    showZapretLoading('Обновление списка сервисов...');

    try {
      await eel.updServc()();
      await loadServices();
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

  safeAddEventListener('gamefilter-group', 'change', checkSettingsChanged);
  safeAddEventListener('auto-update-services-switch', 'change', checkSettingsChanged);
  safeAddEventListener('auto-update-zapret-switch', 'change', checkSettingsChanged);
  safeAddEventListener('save-settings-btn', 'click', saveSettings);
  safeAddEventListener('save-services-btn', 'click', saveServices);

  safeAddEventListener('clear-logs-btn', 'click', clearLogs);

  safeAddEventListener('toggle-btn', 'click', handleToggle);
  safeAddEventListener('save-bypass-btn', 'click', saveBypass);
  safeAddEventListener('autostart-checkbox', 'change', handleAutostart);

  safeAddEventListener('random-gradient-btn', 'click', async () => {
    const hue1 = Math.floor(Math.random() * 360);
    const hue2 = (hue1 + 30 + Math.floor(Math.random() * 60)) % 360;
    const color1 = randomColorFromHue(hue1);
    const color2 = randomColorFromHue(hue2);
    const angle = Math.floor(Math.random() * 360);

    currentTheme = {
      angle: angle,
      start: color1,
      end: color2,
      preset: null,
      type: 'gradient'
    };

    applyTheme(currentTheme);

    try {
      await saveCurrentTheme();
    } catch (error) {
      console.error('Ошибка сохранения темы:', error);
    }

    renderPresets();
  });

  safeAddEventListener('add-background-btn', 'click', openAddBackgroundModal);
  safeAddEventListener('close-add-modal', 'click', closeAddBackgroundModal);
  safeAddEventListener('close-edit-modal', 'click', closeEditColorModal);
  safeAddEventListener('save-background-btn', 'click', saveNewBackground);
  safeAddEventListener('save-color-btn', 'click', saveEditedColor);
  safeAddEventListener('select-bg-file', 'click', selectBackgroundFile);

  document.getElementById('add-background-modal').addEventListener('click', (e) => {
    if (e.target.id === 'add-background-modal') closeAddBackgroundModal();
  });
  document.getElementById('edit-color-modal').addEventListener('click', (e) => {
    if (e.target.id === 'edit-color-modal') closeEditColorModal();
  });
});
