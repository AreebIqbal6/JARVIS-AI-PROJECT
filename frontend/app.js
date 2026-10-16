// J.A.R.V.I.S. Client Controller & WebSocket Telemetry Synchronizer

let ws = null;
let isPowerOn = false;
let isVoiceListening = false;

// DOM Elements
const btnPowerToggle = document.getElementById('btnPowerToggle');
const powerStateText = document.getElementById('powerStateText');
const hardwareType = document.getElementById('hardwareType');
const plugNetDot = document.getElementById('plugNetDot');
const plugModel = document.getElementById('plugModel');
const plugIp = document.getElementById('plugIp');

const valWatts = document.getElementById('valWatts');
const fillWatts = document.getElementById('fillWatts');
const valKwh = document.getElementById('valKwh');
const valVolts = document.getElementById('valVolts');
const valAmps = document.getElementById('valAmps');

const sliderBrightness = document.getElementById('sliderBrightness');
const brightVal = document.getElementById('brightVal');
const btnScanNet = document.getElementById('btnScanNet');
const devicesList = document.getElementById('devicesList');

const chatLog = document.getElementById('chatLog');
const chatInput = document.getElementById('chatInput');
const btnSend = document.getElementById('btnSend');
const btnVoiceToggle = document.getElementById('btnVoiceToggle');
const voiceBtnText = document.getElementById('voiceBtnText');

// 1. WebSocket Telemetry & Chat Loop
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('[J.A.R.V.I.S. WS] Connected to Core Telemetry.');
    plugNetDot.classList.add('on');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'telemetry') {
        updateHardwareUI(msg.data);
      } else if (msg.type === 'chat_message') {
        appendChatMessage('assistant', msg.reply);
      }
    } catch (e) {
      console.error('[WS Parse Error]:', e);
    }
  };

  ws.onclose = () => {
    console.warn('[J.A.R.V.I.S. WS] Disconnected. Reconnecting in 3s...');
    plugNetDot.classList.remove('on');
    setTimeout(initWebSocket, 3000);
  };
}

// 2. Hardware UI Synchronization
function updateHardwareUI(data) {
  if (!data) return;
  const isConnected = Boolean(data.connected);
  isPowerOn = isConnected && Boolean(data.is_on);

  // Power orb
  btnPowerToggle.classList.toggle('active', isPowerOn);
  btnPowerToggle.classList.toggle('offline', !isConnected);
  powerStateText.textContent = isConnected ? (isPowerOn ? 'ON' : 'OFF') : 'OFFLINE';
  powerStateText.classList.toggle('on', isPowerOn);
  
  if (data.model) plugModel.textContent = data.model;
  if (data.ip) plugIp.textContent = data.ip;
  hardwareType.textContent = isConnected ? 'REAL HARDWARE (CONNECTED)' : 'HARDWARE OFFLINE (NO MOCK)';
  hardwareType.style.color = isConnected ? '#00e5ff' : '#ff4444';
  plugNetDot.classList.toggle('on', isConnected);

  // Energy Telemetry - Real values only
  if (data.energy) {
    const w = isConnected ? (data.energy.current_watts || 0) : 0.0;
    valWatts.innerHTML = `${w.toFixed(1)} <span class="unit">W</span>`;
    
    const pct = isConnected ? Math.min(100, Math.max(0, (w / 2000) * 100)) : 0;
    fillWatts.style.width = `${pct}%`;

    const kwh = isConnected ? (data.energy.today_kwh || 0) : 0.0;
    const v = isConnected ? (data.energy.voltage_v || 0) : 0.0;
    const a = isConnected ? (data.energy.current_a || 0) : 0.0;

    valKwh.innerHTML = `${kwh.toFixed(3)} <span class="unit">kWh</span>`;
    valVolts.innerHTML = `${v.toFixed(1)} <span class="unit">V</span>`;
    valAmps.innerHTML = `${a.toFixed(2)} <span class="unit">A</span>`;
  }

  // Brightness
  if (data.brightness !== undefined && isConnected) {
    sliderBrightness.value = data.brightness;
    brightVal.textContent = `${data.brightness}%`;
  } else if (!isConnected) {
    sliderBrightness.value = 0;
    brightVal.textContent = `0%`;
  }
}

// 3. Hardware Controls
btnPowerToggle.addEventListener('click', async () => {
  btnPowerToggle.style.transform = 'scale(0.92)';
  setTimeout(() => btnPowerToggle.style.transform = '', 150);
  try {
    const res = await fetch('/api/plug/toggle', { method: 'POST' });
    const data = await res.json();
    if (data.ok && data.data) {
      isPowerOn = data.data.state === 'on';
      btnPowerToggle.classList.toggle('active', isPowerOn);
      powerStateText.textContent = isPowerOn ? 'ON' : 'OFF';
      powerStateText.classList.toggle('on', isPowerOn);
    }
  } catch (err) {
    console.error('Error toggling power:', err);
  }
});

sliderBrightness.addEventListener('input', (e) => {
  brightVal.textContent = `${e.target.value}%`;
});

sliderBrightness.addEventListener('change', async (e) => {
  try {
    await fetch('/api/plug/brightness', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brightness: parseInt(e.target.value, 10) })
    });
  } catch (err) {
    console.error('Error setting brightness:', err);
  }
});

// Color Presets
document.querySelectorAll('.color-dot').forEach(btn => {
  btn.addEventListener('click', async () => {
    const [r, g, b] = btn.getAttribute('data-rgb').split(',').map(Number);
    // Simple RGB to HSV approximation
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h = 0, s = max === 0 ? 0 : (max - min) / max * 100, v = max / 255 * 100;
    if (max !== min) {
      const d = max - min;
      if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h *= 60;
    }
    try {
      await fetch('/api/plug/color', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hue: Math.round(h), saturation: Math.round(s), value: Math.round(v) })
      });
      appendChatMessage('assistant', `Smart bulb ambience shifted to selected color palette, Sir.`);
    } catch (e) {
      console.error(e);
    }
  });
});

// Wi-Fi Discovery
btnScanNet.addEventListener('click', async () => {
  btnScanNet.textContent = 'SCANNING...';
  try {
    const res = await fetch('/api/plug/discover');
    const data = await res.json();
    if (data.ok && data.devices) {
      devicesList.innerHTML = '';
      if (!data.devices || data.devices.length === 0) {
        devicesList.innerHTML = '<div style="padding: 12px; color: #ff6b6b; font-size: 11px; text-align: center; border: 1px dashed rgba(255, 68, 68, 0.4); border-radius: 8px;">NO PHYSICAL HARDWARE DETECTED ON LOCAL WI-FI (0 FOUND)</div>';
      } else {
        data.devices.forEach(d => {
          const item = document.createElement('div');
          item.className = 'device-item';
          item.innerHTML = `
            <span class="dev-dot ${d.is_on ? 'on' : ''}"></span>
            <span class="dev-name">${d.alias || d.model} (${d.ip})</span>
            <span class="dev-tag">${d.has_energy ? 'ENERGY P110' : 'STANDARD'}</span>
          `;
          devicesList.appendChild(item);
        });
      }
    }
  } catch (e) {
    console.error('Discovery error:', e);
  } finally {
    btnScanNet.textContent = '⟳ SCAN WI-FI';
  }
});

// 4. Chat System
function appendChatMessage(role, text) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-msg ${role}`;
  msgDiv.innerHTML = `
    <div class="msg-author">${role === 'user' ? 'OPERATOR' : 'J.A.R.V.I.S.'}</div>
    <div class="msg-content">${text}</div>
  `;
  chatLog.appendChild(msgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendUserMessage(text) {
  const msg = text || chatInput.value.trim();
  if (!msg) return;

  chatInput.value = '';
  appendChatMessage('user', msg);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    appendChatMessage('assistant', data.response);
  } catch (err) {
    appendChatMessage('assistant', 'Telemetry connection failure. Operating offline, Sir.');
  }
}

btnSend.addEventListener('click', () => sendUserMessage());
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendUserMessage();
});

// Quick Action Chips
document.querySelectorAll('.quick-chips .chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const cmd = chip.getAttribute('data-cmd');
    sendUserMessage(cmd);
  });
});

// 5. Voice Toggle Button
btnVoiceToggle.addEventListener('click', async () => {
  isVoiceListening = !isVoiceListening;
  btnVoiceToggle.classList.toggle('active', isVoiceListening);
  
  if (isVoiceListening) {
    voiceBtnText.textContent = 'VOICE: ACTIVE';
    try {
      await fetch('/api/voice/start', { method: 'POST' });
      appendChatMessage('assistant', 'Microphone audio feed initialized. Speak your commands, Sir.');
    } catch (e) {
      console.error(e);
    }
  } else {
    voiceBtnText.textContent = 'VOICE: STANDBY';
    try {
      await fetch('/api/voice/stop', { method: 'POST' });
      appendChatMessage('assistant', 'Voice listeners disengaged.');
    } catch (e) {
      console.error(e);
    }
  }
});

// Initialize on Load
window.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
});
