const fs = require('fs');
const path = require('path');

const BRAIN_ROOT = path.resolve(__dirname, '../..');
const REGISTRY_PATH = path.join(BRAIN_ROOT, '.agent', 'state', 'linked-projects.json');
const TRACKED_FILES = ['GEMINI.md'];
const TRACKED_SYMLINK_DIRS = ['rules', 'scripts', 'skills', 'workflows'];
const EXPECTED_LIMB_FILES = ['omni-coop.cmd', 'omni-coop.sh', '.agent/state/executor-mode.json'];

function readRegistry() {
  if (!fs.existsSync(REGISTRY_PATH)) return { projects: [] };
  try {
    return JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
  } catch {
    return { projects: [] };
  }
}

function inodeOf(p) {
  try {
    const st = fs.statSync(p);
    return { ino: st.ino, dev: st.dev, exists: true };
  } catch {
    return { ino: null, dev: null, exists: false };
  }
}

function relinkFile(src, dest) {
  try {
    if (fs.existsSync(dest)) fs.unlinkSync(dest);
    fs.linkSync(src, dest);
    return { ok: true, mode: 'hardlink' };
  } catch (err) {
    if (err.code === 'EXDEV' || err.code === 'EPERM') {
      try { fs.copyFileSync(src, dest); return { ok: true, mode: 'copy-fallback' }; }
      catch (e) { return { ok: false, reason: e.message }; }
    }
    return { ok: false, reason: err.message };
  }
}

function verify({ fix = false } = {}) {
  const registry = readRegistry();
  const report = {
    checked: 0,
    drifted: [],
    missing: [],
    healthy: 0,
    fixed: [],
    failed: [],
    symlink_dirs: { ok: 0, broken: [] },
    limb_files: { ok: 0, missing: [] }
  };

  for (const proj of registry.projects || []) {
    if (proj.is_self) continue;

    // 1. Hardlinked tracked files (GEMINI.md)
    for (const fname of TRACKED_FILES) {
      const src = path.join(BRAIN_ROOT, fname);
      const dest = path.join(proj.path, fname);
      report.checked++;

      const srcInfo = inodeOf(src);
      const destInfo = inodeOf(dest);

      if (!destInfo.exists) {
        report.missing.push({ project: proj.path, file: fname });
        if (fix) {
          const r = relinkFile(src, dest);
          if (r.ok) report.fixed.push({ project: proj.path, file: fname, mode: r.mode });
          else report.failed.push({ project: proj.path, file: fname, reason: r.reason });
        }
        continue;
      }

      const sameInode = srcInfo.exists && destInfo.exists && srcInfo.ino === destInfo.ino && srcInfo.dev === destInfo.dev;
      if (sameInode) {
        report.healthy++;
      } else {
        report.drifted.push({ project: proj.path, file: fname, src_ino: srcInfo.ino, dest_ino: destInfo.ino });
        if (fix) {
          const r = relinkFile(src, dest);
          if (r.ok) report.fixed.push({ project: proj.path, file: fname, mode: r.mode });
          else report.failed.push({ project: proj.path, file: fname, reason: r.reason });
        }
      }
    }

    // 2. Symlinked directories (rules/scripts/skills/workflows)
    for (const dirName of TRACKED_SYMLINK_DIRS) {
      const destDir = path.join(proj.path, '.agent', dirName);
      if (!fs.existsSync(destDir)) {
        report.symlink_dirs.broken.push({ project: proj.path, dir: dirName, reason: 'missing' });
        continue;
      }
      try {
        const stat = fs.lstatSync(destDir);
        if (stat.isSymbolicLink() || stat.isDirectory()) {
          report.symlink_dirs.ok++;
        } else {
          report.symlink_dirs.broken.push({ project: proj.path, dir: dirName, reason: 'not a dir/symlink' });
        }
      } catch (e) {
        report.symlink_dirs.broken.push({ project: proj.path, dir: dirName, reason: e.message });
      }
    }

    // 3. Limb-side files (wrappers + executor-mode)
    for (const rel of EXPECTED_LIMB_FILES) {
      const dest = path.join(proj.path, rel);
      if (fs.existsSync(dest)) {
        report.limb_files.ok++;
      } else {
        report.limb_files.missing.push({ project: proj.path, file: rel });
      }
    }
  }

  return report;
}

const fix = process.argv.includes('--fix');
const report = verify({ fix });
console.log(JSON.stringify(report, null, 2));
const unhealthy = (report.drifted.length || report.missing.length || report.symlink_dirs.broken.length || report.limb_files.missing.length);
process.exit(unhealthy && !fix ? 1 : 0);
