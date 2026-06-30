# -*- coding: utf-8 -*-
import os

# Read the HTML content from generate_pdf.py source
src = os.path.join(os.path.dirname(__file__), "generate_pdf.py")
with open(src, "r", encoding="utf-8") as f:
    code = f.read()

# Extract HTML_CONTENT string
marker_start = 'HTML_CONTENT = """'
marker_end = '"""'
idx_start = code.index(marker_start) + len(marker_start)
idx_end = code.index(marker_end, idx_start)
html = code[idx_start:idx_end]

out_path = r"d:\Dev\Workspaces\NCKH\Agent-Generated\DacTa_UseCase.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print("OK: " + out_path)
