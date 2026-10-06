const modules = [
  { name: 'Telegram Gateway', status: 'ready', tone: 'low-risk' },
  { name: 'Weather Briefing', status: 'scheduled', tone: 'automatic' },
  { name: 'GitHub Builder', status: 'daily', tone: 'automation' },
  { name: 'Document OCR', status: 'planned', tone: 'approval' },
  { name: 'Smart Home', status: 'planned', tone: 'approval' },
  { name: 'Local Knowledge', status: 'private', tone: 'local-first' },
];

const demoCommands = [
  ['$ hermes weather', 'Southampton: brief weather card ready.', 'Outdoor note: check rain before leaving.'],
  ['$ hermes github daily', 'Repo: jarvis-hermes-core', 'Action: add safe daily lab note.'],
  ['$ hermes documents', 'OCR workflow: queued as approval-required.', 'No private files are used in this public demo.'],
  ['$ hermes smart-home status', 'Mode: read-only public mock.', 'Device control requires user approval.'],
  ['$ hermes youtube idea', 'Shorts concept: AI command center build log.', 'Output: title + script + description draft.'],
];

function updateClock() {
  const clock = document.querySelector('#clock');
  const now = new Date();
  clock.textContent = now.toLocaleTimeString('en-GB', { hour12: false });
}

function renderModules() {
  const list = document.querySelector('#moduleList');
  list.innerHTML = modules.map((module) => `
    <div class="module-item">
      <div>
        <strong>${module.name}</strong>
        <p>${module.status}</p>
      </div>
      <span class="badge">${module.tone}</span>
    </div>
  `).join('');
}

function renderCommand(index = 0) {
  const terminal = document.querySelector('#terminalOutput');
  const lines = demoCommands[index % demoCommands.length];
  terminal.innerHTML = lines.map((line, lineIndex) => {
    if (lineIndex === 0) return `<p><span>$</span> ${line.replace('$ ', '')}</p>`;
    return `<p>${line}</p>`;
  }).join('');
}

let commandIndex = 0;
document.querySelector('#randomCommand').addEventListener('click', () => {
  commandIndex = (commandIndex + 1) % demoCommands.length;
  renderCommand(commandIndex);
});

updateClock();
renderModules();
renderCommand(0);
setInterval(updateClock, 1000);

// JARVIS LITE INTERACTION
const orb = document.getElementById('mic-btn');
const statusEl = document.getElementById('status');
if (orb && statusEl) {
    orb.addEventListener('click', () => {
        statusEl.innerText = "Listening... (Speak now)";
        // Optional: Trigger Python backend here if running in eel/pywebview
    });
}
