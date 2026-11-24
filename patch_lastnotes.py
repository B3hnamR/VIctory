import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\host.rs')
s = p.read_text(encoding='utf-8')
old = '''            for (n, _) in notes.iter().rev().take(6).rev() {'''
new = '''            let take = if i + 2 >= runs.len() { notes.len() } else { 6 };
            for (n, _) in notes.iter().rev().take(take).rev() {'''
assert old in s
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('ok')
