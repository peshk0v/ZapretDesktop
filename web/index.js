let currentPage = 'home';
let zapretActive = false;
let currentObName = '';
let selectedObName = null;
let oblist = [];
let servicesList = [];
let servicesChanged = false;
let originalSettings = null;
let settingsChanged = false;

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
        document.getElementById('autostart-checkbox').checked = status;
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

    const changed = (currentIPSet !== originalSettings.IPSET) ||
                    (currentGameFilter !== originalSettings.GameFilter);

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
        GameFilter: currentGameFilter
    };

    const saveBtn = document.getElementById('save-settings-btn');
    saveBtn.disabled = true;

    try {
        await eel.savesets(updatedSettings)();
        originalSettings = updatedSettings;
        settingsChanged = false;
        document.getElementById('settings-save-btn-container').style.display = 'none';
    } catch (error) {
        console.error('Ошибка сохранения настроек:', error);
    } finally {
        saveBtn.disabled = false;
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
    await eel.setservc(enabledStates)();
    servicesChanged = false;
    document.getElementById('services-save-button-container').style.display = 'none';
    await loadServices();
}

async function handleAutostart(e) {
    const enabled = e.target.checked;
    await eel.astrt(enabled)();
}

document.addEventListener('DOMContentLoaded', async () => {
  setRandomGradient();

  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      await switchPage(btn.dataset.page);
    });
  });

  document.getElementById('refresh-services-btn').addEventListener('click', async () => {
    const overlay = document.getElementById('services-overlay');
    overlay.style.display = 'flex';

    try {
      await eel.updServc()();
      await loadServices();
    } catch (error) {
      console.error('Ошибка обновления:', error);
    } finally {
      overlay.style.display = 'none';
    }
  });

  document.querySelectorAll('#settings-page input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', checkSettingsChanged);
  });

  await updateUI();

  document.getElementById('gamefilter-switch').addEventListener('change', checkSettingsChanged);
  document.getElementById('save-settings-btn').addEventListener('click', saveSettings);
  document.getElementById('save-services-btn').addEventListener('click', saveServices);
  document.getElementById('toggle-btn').addEventListener('click', handleToggle);
  document.getElementById('autostart-checkbox').addEventListener('change', handleAutostart);
  document.getElementById('save-bypass-btn').addEventListener('click', saveBypass);
});