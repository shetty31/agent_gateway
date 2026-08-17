#!/usr/bin/env python3
from pathlib import Path
p = Path('docs/Runbooks')
for md in p.glob('*.md'):
    s = md.read_text(encoding='utf-8')
    new = s.replace(' ::: ', ':::')
    if new != s:
        md.write_text(new, encoding='utf-8')
        print(f'Fixed spacing in {md}')
