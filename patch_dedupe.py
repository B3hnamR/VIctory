import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\draw.rs')
s = p.read_text(encoding='utf-8')

old = '''                                    if let Some(host) = heap.host() {
                                        let index = v / 32;
                                        if index < host.count() {
                                            let _ = host.mirror(index, address, !compute);
                                        }
                                    }'''
new = '''                                    if let Some(host) = heap.host() {
                                        let index = v / 32;
                                        if index < host.count() && mirror_once(index, address) {
                                            let _ = host.mirror(index, address, !compute);
                                        }
                                    }'''
assert old in s
s = s.replace(old, new, 1)

anchor = '''/// The user-data value of a root argument, as translated shaders read'''
helper = '''/// Whether `index` holds `address` on the host already, or has been mirrored
/// this frame; a root descriptor reaches the same slot from every draw.
fn mirror_once(index: u32, address: u64) -> bool {
    use std::collections::HashSet;
    use std::sync::{Mutex, OnceLock};
    static SEEN: OnceLock<Mutex<(u64, HashSet<(u32, u64)>)>> = OnceLock::new();
    let seen = SEEN.get_or_init(|| Mutex::new((0, HashSet::new())));
    let mut seen = seen.lock().unwrap_or_else(|e| e.into_inner());
    let frame = crate::queue::presented();
    if seen.0 != frame {
        seen.0 = frame;
        seen.1.clear();
    }
    seen.1.insert((index, address))
}

'''
assert anchor in s
s = s.replace(anchor, helper + anchor, 1)
p.write_text(s, encoding='utf-8')
print('ok')
