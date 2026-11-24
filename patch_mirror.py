import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\draw.rs')
s = p.read_text(encoding='utf-8')
old = '''            let n = entries
                .iter()
                .map(|u| u.table_offset_dwords / 8)
                .chain(selected.last().copied())
                .max()
                .unwrap_or(0)
                + 1;'''
new = '''            let mut n = entries
                .iter()
                .map(|u| u.table_offset_dwords / 8)
                .chain(selected.last().copied())
                .max()
                .unwrap_or(0)
                + 1;
            // Diagnostics: a shader can reach a slot through an index the
            // program computes, which no used entry or constant names.
            if std::env::var_os("VICTORY_MIRROR_ALL").is_some() {
                n = host.count();
            }'''
assert old in s
s = s.replace(old, new, 1)
# every table must be rebuilt for the wide range to matter
old2 = '''        fresh.sort_unstable();
        fresh.dedup();'''
new2 = '''        if std::env::var_os("VICTORY_MIRROR_ALL").is_some() {
            fresh.extend(used.iter().filter(tables).map(|u| u.slot));
        }
        fresh.sort_unstable();
        fresh.dedup();'''
assert old2 in s
s = s.replace(old2, new2, 1)
p.write_text(s, encoding='utf-8')
print('ok')
