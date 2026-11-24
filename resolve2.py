import pathlib, re

files = [r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\shader_cache.rs',
         r'D:\ABDM\wt-victory-prwave\crates\victory-shader\src\emit\lower.rs',
         r'D:\ABDM\wt-victory-prwave\crates\victory-shader\src\emit\mod.rs',
         r'D:\ABDM\wt-victory-prwave\crates\victory-shader\src\emit\valu_tests.rs']

for f in files:
    p = pathlib.Path(f)
    s = p.read_text(encoding='utf-8')
    s = re.sub(r'<<<<<<< ours\n(.*?)=======\n(.*?)>>>>>>> theirs\n',
               lambda m: m.group(2) + m.group(1), s, flags=re.S)
    p.write_text(s, encoding='utf-8')
    print(f, s.count('<<<<<<<'))
