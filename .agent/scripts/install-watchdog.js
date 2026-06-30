const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const TASK_NAME = 'OmniWatchdog';
const WATCHDOG_SCRIPT = path.resolve(__dirname, 'watchdog.js');
const BRAIN_ROOT = path.resolve(__dirname, '../..');
const LOG_DIR = path.join(BRAIN_ROOT, '.agent', 'state');
const LOG_FILE = path.join(LOG_DIR, 'watchdog.log');

if (process.platform !== 'win32') {
  console.error('Installer này dành cho Windows. Linux/macOS: dùng systemd hoặc launchd manually.');
  console.log('Manual run: nohup node .agent/scripts/watchdog.js > .agent/state/watchdog.log 2>&1 &');
  process.exit(1);
}

if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

const action = process.argv[2] || 'install';

function findNode() {
  const r = spawnSync('where', ['node'], { encoding: 'utf8' });
  if (r.status !== 0) {
    console.error('Không tìm thấy node trong PATH.');
    process.exit(1);
  }
  return r.stdout.trim().split(/\r?\n/)[0];
}

if (action === 'install') {
  const nodeExe = findNode();
  const cmd = `cmd /c \"\"${nodeExe}\" \"${WATCHDOG_SCRIPT}\" >> \"${LOG_FILE}\" 2>&1\"`;
  const args = [
    '/Create',
    '/TN', TASK_NAME,
    '/SC', 'ONLOGON',
    '/RL', 'LIMITED',
    '/F',
    '/TR', cmd
  ];
  const r = spawnSync('schtasks', args, { encoding: 'utf8' });
  if (r.status === 0) {
    console.log(`[+] Đã đăng ký Scheduled Task '${TASK_NAME}'. Sẽ tự chạy mỗi lần đăng nhập.`);
    console.log(`    Log: ${LOG_FILE}`);
    console.log(`    Start ngay: node .agent/scripts/install-watchdog.js start`);
  } else {
    console.error('[-] schtasks /Create thất bại:', r.stderr || r.stdout);
    process.exit(r.status || 1);
  }
} else if (action === 'uninstall') {
  const r = spawnSync('schtasks', ['/Delete', '/TN', TASK_NAME, '/F'], { encoding: 'utf8' });
  if (r.status === 0) console.log(`[+] Đã gỡ Scheduled Task '${TASK_NAME}'.`);
  else { console.error('[-] Uninstall thất bại:', r.stderr || r.stdout); process.exit(r.status || 1); }
} else if (action === 'start') {
  const r = spawnSync('schtasks', ['/Run', '/TN', TASK_NAME], { encoding: 'utf8' });
  if (r.status === 0) console.log(`[+] Watchdog đã chạy. Tail log: powershell Get-Content -Wait "${LOG_FILE}"`);
  else { console.error('[-] Start thất bại:', r.stderr || r.stdout); process.exit(r.status || 1); }
} else if (action === 'status') {
  const r = spawnSync('schtasks', ['/Query', '/TN', TASK_NAME, '/V', '/FO', 'LIST'], { encoding: 'utf8' });
  console.log(r.stdout || r.stderr);
} else {
  console.error('Usage: node install-watchdog.js <install|uninstall|start|status>');
  process.exit(1);
}
