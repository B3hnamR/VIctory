import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\draw.rs')
s = p.read_text(encoding='utf-8')
old = '''                        None => self.user_value(compute, u.slot, u.root, u.dword),
                    };'''
new = '''                        None => {
                            let v = self.user_value(compute, u.slot, u.root, u.dword);
                            // A root descriptor reaches the shader as an index
                            // into the bound heap (`createHandleFromHeap`); the
                            // slot must hold our view, and only the used-resource
                            // entries are mirrored otherwise.
                            if u.root != RootType::Table {
                                if let (Some(&Root::View(address)), Some(heap)) = (
                                    self.roots_ref(compute).get(usize::from(u.slot)),
                                    self.heaps[0].ne(0).then(|| {
                                        crate::descriptor::heap(self.heaps[0] as This)
                                    }),
                                ) {
                                    if let Some(host) = heap.host() {
                                        let _ = host.mirror(v / 32, address, !compute);
                                    }
                                }
                            }
                            v
                        }'''
assert old in s
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('ok')
