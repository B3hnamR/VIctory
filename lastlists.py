import re

s = re.sub(r'\x1b\[[0-9;]*m', '', open(r'D:\ABDM\logs\vic-main\stderr-20261124-194912.log', encoding='utf8', errors='replace').read())
blocks = list(re.finditer(r'slow host submission ms=(\d+) lists=(\d+) pipelines=(\{[^}]*\})', s))
print('blocks', len(blocks))
for m in blocks[-2:]:
    print('---', m.group(1), 'ms', m.group(2), 'lists')
    print(m.group(3)[:1200])
