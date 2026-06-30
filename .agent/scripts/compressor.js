const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = process.cwd();
const MAX_FINDINGS_CHARS = 1500;
const MAX_LINE_CHARS = 200;

const FILLER_PATTERNS = [
  /\bI (looked at|searched|found that|noticed|observed)\b/gi,
  /\b(basically|actually|simply|just|really|essentially)\b/gi,
  /\b(it seems|it appears|it looks like|I think|I believe)\b/gi,
  /\b(so|well|now|then),?\s+/gi,
  /\b(here's|here is|here are) (what|the)\b/gi,
  /\bbased on (my|the) (analysis|review|investigation)\b/gi
];

function stripFiller(text) {
  let out = text;
  FILLER_PATTERNS.forEach(p => { out = out.replace(p, ''); });
  return out.replace(/\s+/g, ' ').trim();
}

function isCodeBlock(line) {
  return /^```/.test(line) || /^    [^\s]/.test(line);
}

function isFactLine(line) {
  return /[\w/.-]+:\d+:/.test(line) || /^no_match:/i.test(line);
}

function compress(raw) {
  const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

  let inCodeBlock = false;
  let codeBlockLines = 0;
  const kept = [];

  for (const line of lines) {
    if (/^```/.test(line)) {
      inCodeBlock = !inCodeBlock;
      codeBlockLines = 0;
      continue;
    }
    if (inCodeBlock) {
      codeBlockLines++;
      if (codeBlockLines > 5) continue;
    }
    if (line.length > MAX_LINE_CHARS) continue;

    const cleaned = stripFiller(line);
    if (!cleaned) continue;
    if (cleaned.length < 5) continue;

    kept.push(cleaned);
  }

  const facts = kept.filter(isFactLine);
  const others = kept.filter(l => !isFactLine(l));
  const ordered = [...facts, ...others];

  let total = 0;
  const final = [];
  for (const line of ordered) {
    const newLen = total + line.length + 1;
    if (newLen > MAX_FINDINGS_CHARS) break;
    final.push(line);
    total = newLen;
  }

  return final.join('\n');
}

function compressionStats(raw, compressed) {
  return {
    raw_chars: raw.length,
    compressed_chars: compressed.length,
    ratio: compressed.length > 0 ? (raw.length / compressed.length).toFixed(2) : 'inf',
    cap: MAX_FINDINGS_CHARS,
    cap_used_pct: ((compressed.length / MAX_FINDINGS_CHARS) * 100).toFixed(1)
  };
}

const action = process.argv[2];

if (action === 'compress') {
  const inputPath = process.argv[3];
  if (!inputPath) {
    console.error('Usage: node compressor.js compress <input.txt> [--write-task]');
    process.exit(1);
  }
  if (!fs.existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    process.exit(1);
  }
  const raw = fs.readFileSync(inputPath, 'utf8');
  const compressed = compress(raw);
  const stats = compressionStats(raw, compressed);

  if (process.argv.includes('--write-task')) {
    const taskPath = path.join(WORKSPACE_DIR, 'task.json');
    if (!fs.existsSync(taskPath)) {
      console.error('No task.json to update.');
      process.exit(1);
    }
    const task = JSON.parse(fs.readFileSync(taskPath, 'utf8'));
    task.findings = compressed;
    console.log(JSON.stringify({ stats, preview: compressed.split('\n').slice(0, 3) }, null, 2));
    console.log('\n--- Pass this to task-manager.js write ---');
    console.log(JSON.stringify(task));
  } else {
    console.log(JSON.stringify({ stats, compressed }, null, 2));
  }
} else if (action === 'stdin') {
  let raw = '';
  process.stdin.on('data', chunk => { raw += chunk; });
  process.stdin.on('end', () => {
    const compressed = compress(raw);
    console.log(compressed);
  });
} else {
  console.error('Usage:');
  console.error('  node compressor.js compress <file> [--write-task]');
  console.error('  node compressor.js stdin  (read raw from stdin, write compressed to stdout)');
  process.exit(1);
}
