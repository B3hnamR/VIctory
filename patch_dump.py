import pathlib

p = pathlib.Path(r'D:\ABDM\wt-victory-prwave\crates\victory-gpu\src\pipeline.rs')
s = p.read_text(encoding='utf-8')
old = '''                    Ok(t) => tracing::info!(
                        stage = self.stage,
                        hash = %self.hash,
                        user_data = t.host.user_data.len(),
                        samplers = t.host.samplers.len(),
                        "shader translated"
                    ),'''
new = '''                    Ok(t) => {
                        tracing::info!(
                            stage = self.stage,
                            hash = %self.hash,
                            user_data = t.host.user_data.len(),
                            samplers = t.host.samplers.len(),
                            "shader translated"
                        );
                        // Diagnostics: `VICTORY_DUMP_SHADER=<dir>` keeps every
                        // container, for offline replay.
                        if let Some(dir) = std::env::var_os("VICTORY_DUMP_SHADER") {
                            let path = std::path::Path::new(&dir)
                                .join(format!("{}-{}.dxbc", self.stage, self.hash));
                            let _ = std::fs::write(path, &self.container);
                        }
                    }'''
assert old in s
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('ok')
