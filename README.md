# VIctory

Runs Grand Theft Auto VI (Xbox Series X|S) natively on Windows, from files
the user supplies.

The title's x86-64 code runs unchanged inside our process; VIctory supplies
the platform underneath it and converts the title's data, ahead of time where
it can and on first use where it must (shaders). See
[docs/architecture.md](docs/architecture.md).

## Fork test results (2026-11-24)

**No playable 3D world was observed on our RTX 3080.** This fork tracks
[Marvisak/VIctory](https://github.com/Marvisak/VIctory). Its `main` includes
the wave32 lane-mask implementation from [upstream PR #298](https://github.com/Marvisak/VIctory/pull/298),
our [seven-case regression](https://github.com/permadiego/VIctory/pull/1), and
an independent [D3D12 texture-handoff fixture](crates/victory-gpu/src/bin/texture-handoff.rs).
None of them is a gameplay fix.

**Machine:** Windows 11, Ryzen 7 5800X, 32 GB RAM, RTX 3080 (10 GB), driver 610.88.
These are individual runs, not benchmarks. FPS measures presentations, including
loading screens. Memory is process commit / sampled dedicated GPU memory in MiB.

| Project / tested revision | Furthest visible stage | Presentation rate | Commit / VRAM | Observed failure |
|---|---|---|---|---|
| [VIctory `ffe310e`](https://github.com/Marvisak/VIctory/commit/ffe310e) | Vice City title card, then black with audio | 27.1 FPS (2,047 intervals / 75.49 s during loading) | 22,174 / 8,509 | `DXGI_ERROR_DEVICE_HUNG` |
| [XCL `8cada26`](https://github.com/ivall/xcl/commit/8cada26) | Illustrated loading screen; no automated input verified | 26.0 FPS (7,920 presents / 304.89 s) | 16,510 / 7,337 | `DXGI_ERROR_DEVICE_HUNG` |
| [XCL `47efa2e`](https://github.com/ivall/xcl/commit/47efa2e) | Illustrated loading screen; one verified Enter at the player picker | 11.4 FPS (1,700 presents / 148.76 s) | 28,100 / 7,859 | `0xC0000005`, null write. Last complete image was 41.5 s before exit. |

### Reproduce without game files

```powershell
cargo test --profile diag -p victory-shader --lib wave32_spilled_mask_guards_the_restored_lanes
$env:VICTORY_HANDOFF_ADAPTER = 'RTX 3080' # Optional: substring of the Windows adapter name
cargo run --profile diag -p victory-gpu --bin texture-handoff
```

The shader regression checks the guard *after* restoring the mask, not just
whether translation succeeds. It failed on the parent (`ffe310e`) and passed on
the PR head (`54f97db`); with the added regression, the shader library suite
passed 121 tests with one benchmark ignored. Two previously rejected pixel
shaders emitted valid DXIL on that PR head. Their binaries are not distributed.

The hardware fixture uses two D3D12 queues, synthetic patterns and a bounded
fence wait. On the RTX 3080 the early read returned the old pattern, the
ordered read returned the new pattern, and the wrong texture returned the decoy:
**1,024/1,024 texels matched in each case**. The test design draws on
[Xbox2Windows' ordered/early readback](https://github.com/R0Y00/Xbox2Windows/blob/3c6273ac1/tests/vm_copy_queue_check.cpp)
and [stale texture control](https://github.com/R0Y00/Xbox2Windows/blob/3c6273ac1/tests/compute_mesh_texture_check.py).
We reviewed those sources; we did not run Xbox2Windows against the game.

### Experimental renderer findings

The following measurements used a **separate local integration**, not this
fork's `main`: VIctory [#439](https://github.com/Marvisak/VIctory/pull/439)
(wave width), [#704](https://github.com/Marvisak/VIctory/pull/704) (buffer stride),
[#571](https://github.com/Marvisak/VIctory/pull/571) (shared-memory writes),
and [#638](https://github.com/Marvisak/VIctory/pull/638) (producer tracing).
Both repaired pixel pipelines were accepted and submitted in-game. An intermediate
color target showed poles and fencing, but the presented image remained black.
In a pass-time capture, two full-resolution inputs were all zero before the
final color pass; its output peaked at 4/1023 per RGB channel.

In one trace, 173 command-list memory waits saw a 64-bit value below the
reference at submission; later submissions wrote the exact requested value at
the same address in all 173 cases. [XCL's wait decoder](https://github.com/ivall/xcl/blob/8cada26/crates/xcl/src/hle/d3d12x/list_x.rs)
treats comparison 7 as `>=`. The observations are **not** GPU-instruction-time
samples or proof that a missed wait caused the black frame.

In a separate run we logged the effective buffer ranges bound to shader views.
On frames 1812 and 1821 the compute writer `91b10a73e48b2192` bound UAVs of
764 and 22,164 bytes, respectively. On each frame the first recorded overlap
in a later submission was `17af15c4015cb4b6` at SRV `s0+688`. On frame 1821
that SRV covered 182,452,224 bytes and the same shader also bound that pool as
a UAV. A bound view this broad does not identify which elements were accessed.
The presented frame remained black. The next discriminator is the shader's
runtime index or a readback of the relevant subrange, not a global queue stall.

[The offline analyzer](tools/trace_buffer_readers.py) accepts experimental
VIctory logs containing `wait neighbor` and `writer event` markers. It compares
title addresses only within one frame and strictly later submissions. It labels
enclosing-resource spans separately from effective views; an absent match does
not exclude indirect, unmarked, same-submission or cross-frame consumers.

```powershell
python -B tools/test_trace_buffer_readers.py
python -B tools/trace_buffer_readers.py <local-diagnostic-log> --frame <frame-number>
```

## Upstream status (2026-11-23)

**Not playable yet.** The title boots, runs its menus at its own 30 fps and
loads the world, where rendering fails.

| Stage | State |
|-------|-------|
| Boot, first-boot screens (accessibility, language, settings, legal) | works, 30 fps |
| Intro video with sound | works |
| Start screen, profile and saves | works |
| Loading into the world (about 50 s) | works |
| The world (first mission's intro) | reached and runs with indirect draws; its title card renders, the scene after it is still dark; 0.5-1.8 s per frame |

Tested on one machine: Windows 11, AMD RX 6700 XT.

> **Warning.** Entering the world on a real GPU can currently hang it, and
> Windows then resets the display driver (every monitor goes black for a
> moment). To look further, use a diagnostics build with
> `VICTORY_D3D12_WARP=1`, which renders on the software adapter.

What each part does today and what it still needs:

| Subsystem | Today | Needs |
|-----------|-------|-------|
| Loader | Runs the title's executable and its DLLs in our process; crash reports name the faulting code and are kept in `crashes.log` | – |
| Runtime services | One signed-in offline user, licences, packages, saves that survive a kill at any step, text entry dialog | Speech is silent; the dialog and relaunch are untested live |
| Network | Offline by design: the title cannot reach the network | – |
| Files and streaming | Archives and streamed data read, zlib and BCPack decoded in parallel | Loading is limited by writes into title memory |
| Input | XInput pads, keyboard, keyboard stand-in pad | Trigger rumble |
| Audio | Menu, video and loading sound; XMA voices and Opus streams decode | Reverb is silent; Opus results unverified against the title |
| GPU: menus | Draws, compute and presentation on host D3D12; only changed title memory is copied | Frame pacing drifts on one screen in release builds |
| GPU: world | Mesh pipelines, shader-written buffers, descriptor lifetimes, indirect execution (arguments clamped), pipelines made by worker threads and kept on disk | Most of the scene is still missing (untranslated shaders drop draws); frames take seconds; real queries, depth bounds, HDR and scaling are missing |
| Shaders | Console GPU code recompiled to DXIL at first use, cached on disk. Menus: all. World: mesh 8,191 of 8,506, vertex/pixel 10,617 of 12,346, compute 1,643 of 2,539 | 64-bit image atomics, merged geometry stages, the ray-tracing builder's shaders; some compute programs need a GPU with 64-lane waves |
| Textures | Console tiled layouts and detiling for the modes the title uses | Render-target metadata planes |
| Series S mode | Runs through the menus to the loading screen | The world, as above |

## Getting started

Requirements: Windows 10/11 x64, a CPU with AVX2, a Direct3D 12 GPU with
shader model 6.6 (and mesh shaders for the world), Rust (pinned in
`rust-toolchain.toml`).

The title also needs several GiB of available Windows commit at startup.
Check **Committed** under **Task Manager → Performance → Memory**. If
`crashes.log` reports Windows error 1455, close other applications or increase
the Windows paging file size, then retry.

```powershell
cargo xtask install-hooks                # asset-policy check on every commit
copy victory.example.toml victory.toml   # then set your paths (outside the repo)
cargo test --workspace                   # needs no game data
cargo run -p victory -- config           # check your paths
```

Run the title:

```powershell
cargo build --release -p victory
target\release\victory.exe run <game dir>\<the title's exe> --execute
```

The window caption shows the framerate. Saves, settings and `crashes.log`
are kept under the data folder (default `%LOCALAPPDATA%\victory\data`), derived
data under the cache folder.

Input: XInput pads. With none connected the keyboard is a pad while the
title's window has focus:

| Keys | Pad |
|------|-----|
| W A S D / I J K L | left / right stick |
| arrows | D-pad |
| Enter, Backspace, X, Y | A, B, X, Y |
| Q / E, Z / C | shoulders, triggers |
| F / H | stick clicks |
| Esc, Tab | Menu, View |

## Commands

```
victory inspect <exe|dll> [--imports] [--exports]
victory census [paths...] [--missing] [--strict]
victory lib-exports <import.lib> [--list]
victory shader-info [paths...] [--verbose] [--disasm]
victory translate [paths...] [--validate] [--pipelines] [--list] [--jobs N]
victory run <exe> [--execute] [--unimplemented trap|zero] [--strict]
            [--console series-x|series-s] [-- <title arguments>]
victory config
```

Logging: `VICTORY_LOG=victory_loader=trace,info` (a release build logs
info and above).

## Debugging

A release build has no debugging aids. Build them in with

```powershell
cargo build --profile diag -p victory --features diagnostics   # target\diag\victory.exe
```

| Variable | Effect |
|----------|--------|
| `VICTORY_LOG=<target>=debug,...` | debug and trace output |
| `VICTORY_STACKS=20,60` | every thread's stack at those seconds |
| `VICTORY_WATCH=<rva>,...` | logs a title u32 when it changes |
| `VICTORY_KEYS=30:Enter,35:X` | presses keys at those seconds, focus or not |
| `VICTORY_CRASH_SAVE=<rva>:<len>,...` | saves title memory to the cache folder on a crash |
| `VICTORY_CAPTURE=<dir>` | saves presented frames (powers of two, or `VICTORY_CAPTURE_FRAMES=<list>`) |
| `VICTORY_DUMP_TARGETS=1` | with the two above, saves every render target of those frames |
| `VICTORY_D3D12_DEBUG=1` | host debug layer |
| `VICTORY_D3D12_GBV=1` | with the above, GPU-based validation (bad descriptor use reported, not faulted; slow) |
| `VICTORY_D3D12_DRED=1` | on a GPU failure, the allocation hit and the commands in flight |
| `VICTORY_SKIP_PIPELINES=<hash>,...` | omit draws and dispatches, including indirect ones, whose pipeline contains a listed 16-digit shader hash |
| `VICTORY_GPU_TIMING=1` | with the above, each list of a submission run and timed on its own; slow lists logged with their slowest commands |
| `VICTORY_D3D12_WARP=1` | host device on the software adapter (slow; cannot reset the driver) |
| `VICTORY_SHADER_LOOP_LIMIT=<n>` | translated shader loops stop after `n` iterations per lane instead of 2^20 (own shader cache entries); if a lower `n` makes world frames much faster, loops hitting the limit are what makes them slow |
| `VICTORY_AUDIO_CAPTURE=<file.wav>` | records what the title plays (our process only) |
| `VICTORY_XMA_DUMP=<dir>` | saves the first 32 XMA voices' context and input |

Every build appends crashes and host GPU failures to `crashes.log` in the
title's data folder.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
