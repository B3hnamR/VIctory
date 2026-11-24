import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\draw.rs')
s = p.read_text(encoding='utf-8')

old = '''                                        if index < host.count() && mirror_once(index, address) {
                                            let _ = host.mirror(index, address, !compute);
                                        }'''
new = '''                                        if index < host.count() {
                                            let filled = host.describe_slot(index).is_some();
                                            if !filled || mirror_once(index, address) {
                                                let _ = host.mirror(index, address, !compute);
                                            }
                                        }'''
assert old in s
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('ok')
