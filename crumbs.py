import re

s = re.sub(r'\x1b\[[0-9;]*m', '', open(r'D:\ABDM\logs\vic-main\stderr-20261124-194912.log', encoding='utf8', errors='replace').read())
i = s.rfind('breadcrumbs (done/count, list)')
seg = s[i:i + 300000]
e = re.findall(r'"(\d+)/(\d+) (.*?)"', seg)
print('entries', len(e))
print('incomplete', [(n, d, l) for n, d, l in e if int(d) < int(n)][:10])
print('last 3', e[-3:])
print('with list', [x for x in e if x[2] != 'None'][:5])
