import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-shader\src\emit\lower.rs')
s = p.read_text(encoding='utf-8')
old = '''            } else if console_lanes || one_wave && s.lds_dwords > 0 {
                s.wave_size = Some(wave);
            }'''
new = '''            } else if one_wave && total <= 32 {
                // One wave that fits the host's width needs no 64-lane claim.
                s.wave_size = Some(32);
            } else if console_lanes || one_wave && s.lds_dwords > 0 {
                s.wave_size = Some(wave);
            }'''
assert old in s
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('ok')
