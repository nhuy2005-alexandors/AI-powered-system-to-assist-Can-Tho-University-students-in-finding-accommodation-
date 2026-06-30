const fs = require('fs');
const path = require('path');

const errorsFilePath = path.resolve(__dirname, '../../ERRORS.md');

function escapeFence(s) {
  return String(s).replace(/```/g, '``​`');
}

function escapeInline(s) {
  return String(s).replace(/`/g, "'");
}

const type = escapeInline(process.argv[2] || 'Unknown');
const severity = escapeInline(process.argv[3] || 'Medium');
const location = escapeInline(process.argv[4] || 'Unknown Location');
const agent = escapeInline(process.argv[5] || 'System');
const message = escapeFence(process.argv[6] || 'No message provided');

const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 16);

const logEntry = `
## [${timestamp}] - ${type} Error

- **Type**: ${type}
- **Severity**: ${severity}
- **File/Location**: \`${location}\`
- **Agent**: ${agent}
- **Error Message**:
  \`\`\`
  ${message}
  \`\`\`
- **Status**: Investigating

---
`;

try {
  if (!fs.existsSync(errorsFilePath)) {
    fs.writeFileSync(errorsFilePath, '# Error Logs\n\n---\n');
  }
  fs.appendFileSync(errorsFilePath, logEntry);
  console.log(`[+] Đã ghi log lỗi vào ERRORS.md thành công.`);
} catch (error) {
  console.error(`[-] Không thể ghi file ERRORS.md:`, error.message);
}
