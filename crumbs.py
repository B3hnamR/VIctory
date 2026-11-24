import re, sys

s = re.sub(r'\x1b\[[0-9;]*m', '', open(sys.argv[1], encoding='utf8', errors='replace').read())
i = s.rfind('breadcrumbs (done/count, list)')
seg = s[i:i + 300000]
e = re.findall(r'"(\d+)/(\d+) (.*?)"', seg)
print('entries', len(e), 'last', e[-2:] if e else None)
print('total incomplete', len([1 for n, d, _ in e if int(d) < int(n)]))
print('last incomplete', [x for x in e if int(x[1]) < int(x[0])][-3:])
