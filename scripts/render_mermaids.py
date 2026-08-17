#!/usr/bin/env python3
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOKS = ROOT / 'docs' / 'Runbooks'
OUTDIR = ROOT / '.run_mermaid'
OUTDIR.mkdir(exist_ok=True)

pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)

results = []
any_fail = False

for md in sorted(RUNBOOKS.glob('*.md')):
    text = md.read_text(encoding='utf-8')
    blocks = pattern.findall(text)
    for i, block in enumerate(blocks, start=1):
        name = f"{md.stem}_block{i}"
        mmd = OUTDIR / f"{name}.mmd"
        svg = OUTDIR / f"{name}.svg"
        mmd.write_text(block, encoding='utf-8')
        # Try to run npx mermaid-cli
        cmd = ['npx', '-y', '@mermaid-js/mermaid-cli', '-i', str(mmd), '-o', str(svg)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            results.append((md.name, i, 'ok', ''))
        except subprocess.CalledProcessError as e:
            any_fail = True
            err = e.stderr or e.stdout
            results.append((md.name, i, 'fail', err))

# Print summary
for r in results:
    fname, idx, status, msg = r
    if status == 'ok':
        print(f"{fname} block {idx}: OK")
    else:
        print(f"{fname} block {idx}: FAIL")
        print(msg)

if any_fail:
    print('\nSome diagrams failed to render. See details above and check .run_mermaid/ for inputs.')
    raise SystemExit(2)
else:
    print('\nAll diagrams rendered successfully. SVGs are in .run_mermaid/')
    raise SystemExit(0)
