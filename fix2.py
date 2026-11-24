import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-shader\src\emit\lower.rs')
s = p.read_text(encoding='utf-8')
old = '''                            if n == "v_readlane_b32"
                                || (n == "v_readfirstlane_b32"
                                    && !inst
                                        .writes
                                        .first()
                                        .is_some_and(|w| x.res.waterfall.reads.contains(&w.1)))'''
new = '''                            if n == "v_readlane_b32" || n == "v_readfirstlane_b32"'''
assert old in s
s = s.replace(old, new, 1)
old2 = '            if (32..64).contains(&x.max_wave) && x.native.wave64 {'
new2 = '''            let uniform_cf = uniform_blocks(p, x.st).first().copied().unwrap_or(false);
            if (32..64).contains(&x.max_wave) && x.native.wave64 {'''
assert old2 in s
s = s.replace(old2, new2, 1)
p.write_text(s, encoding='utf-8')

q = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-shader\src\emit\mod.rs')
t = q.read_text(encoding='utf-8')
old3 = '''    let io = io::raise(&p, &native)?;
    let st = st?;'''
new3 = '''    let io = io::raise(&p, &native)?;
    let st = structure::structure(&p);
    let st = st?;'''
assert old3 in t
t = t.replace(old3, new3, 1)
q.write_text(t, encoding='utf-8')
print('ok')
