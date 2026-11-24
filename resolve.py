import pathlib, re

both = {r'crates\victory-gpu\src\host.rs'}
files = [r'crates\victory-gpu\src\host.rs', r'crates\victory-shader\src\emit\lower.rs',
         r'crates\victory-shader\src\emit\mod.rs', r'crates\victory-shader\src\emit\valu_tests.rs']

for f in files:
    p = pathlib.Path(f)
    s = p.read_text(encoding='utf-8')
    if f in both:
        s = re.sub(r'<<<<<<< ours\n(.*?)=======\n(.*?)>>>>>>> theirs\n',
                   lambda m: m.group(2) + m.group(1), s, flags=re.S)
    else:
        s = re.sub(r'<<<<<<< ours\n(.*?)=======\n(.*?)>>>>>>> theirs\n',
                   lambda m: m.group(2), s, flags=re.S)
    p.write_text(s, encoding='utf-8')
    print(f, s.count('<<<<<<<'))
