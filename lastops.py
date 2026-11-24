import re, sys

s = re.sub(r'\x1b\[[0-9;]*m', '', open(sys.argv[1], encoding='utf8', errors='replace').read())
i = s.rfind('breadcrumbs (done/count')
seg = s[i:i + 20000]
m = re.findall(r'"; list (\d+) of (\d+), of its (\d+): ((?:dispatch|draw|mesh|indirect)[^"]{0,120})', seg)
print('detail pairs', len(m))
for x in m[-3:]:
    print(x[0], '/', x[1], 'of', x[2], ':', x[3][:140])
