import pathlib, re

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\draw.rs')
s = p.read_text(encoding='utf-8')

body = '''fn readable(list: &HostList, kind: ResourceType, view: &View) {
    #[cfg(feature = "diagnostics")]
    if kind == ResourceType::Uav {
        crate::producers::live_write(view);
    } else {
        crate::producers::read(view);
    }
'''

s = re.sub(r'<<<<<<< ours\n(.*?)=======\n(.*?)>>>>>>> theirs\n', lambda m: body, s, flags=re.S, count=1)
p.write_text(s, encoding='utf-8')
print('left', s.count('<<<<<<<'))
