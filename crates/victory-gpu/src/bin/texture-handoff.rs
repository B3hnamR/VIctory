//! Standalone D3D12 control: identical consumer, different producer order or SRV.
#[cfg(not(windows))]
fn main() {
    panic!("D3D12 required");
}

#[cfg(windows)]
fn main() -> anyhow::Result<()> {
    probe::run()
}

#[cfg(windows)]
mod probe {
    use anyhow::{Context, Result, ensure};
    use std::{
        mem::{ManuallyDrop, transmute_copy},
        ptr, slice,
        time::{Duration, Instant},
    };
    use windows::{
        Win32::Graphics::{
            Direct3D::{D3D_FEATURE_LEVEL_12_0, Fxc::D3DCompile, ID3DBlob},
            Direct3D12::*,
            Dxgi::{Common::*, *},
        },
        core::{Interface, PCSTR, s},
    };

    const N: usize = 32 * 32;
    const OLD: u32 = 0x11000000;
    const NEW: u32 = 0x22000000;
    const DECOY: u32 = 0x33000000;
    const HLSL: &str = r#"
    #define ROOT "DescriptorTable(UAV(u0)),DescriptorTable(SRV(t0)),UAV(u1),RootConstants(num32BitConstants=1,b0)"
    RWTexture2D<uint> dst : register(u0); Texture2D<uint> src : register(t0);
    RWByteAddressBuffer sampled : register(u1); cbuffer Params : register(b0) { uint tag; }
    [RootSignature(ROOT)] [numthreads(8,8,1)] void produce(uint3 id:SV_DispatchThreadID) {
        dst[id.xy] = tag + id.y * 32 + id.x;
    }
    [RootSignature(ROOT)] [numthreads(8,8,1)] void consume(uint3 id:SV_DispatchThreadID) {
        sampled.Store(4 * (id.y * 32 + id.x), src.Load(int3(id.xy,0)));
    }"#;

    fn compile(entry: PCSTR) -> Result<Vec<u8>> {
        // SAFETY: source and entry point stay live; each returned blob owns its bytes.
        unsafe {
            let mut blob: Option<ID3DBlob> = None;
            let mut error: Option<ID3DBlob> = None;
            if let Err(e) = D3DCompile(
                HLSL.as_ptr().cast(),
                HLSL.len(),
                s!("texture-handoff"),
                None,
                None,
                entry,
                s!("cs_5_1"),
                0,
                0,
                &mut blob,
                Some(&mut error),
            ) {
                if let Some(b) = error {
                    eprintln!(
                        "{}",
                        String::from_utf8_lossy(slice::from_raw_parts(
                            b.GetBufferPointer().cast(),
                            b.GetBufferSize()
                        ))
                    );
                }
                return Err(e.into());
            }
            let b = blob.context("missing shader")?;
            Ok(slice::from_raw_parts(b.GetBufferPointer().cast(), b.GetBufferSize()).to_vec())
        }
    }

    fn transition(
        list: &ID3D12GraphicsCommandList,
        r: &ID3D12Resource,
        before: D3D12_RESOURCE_STATES,
        after: D3D12_RESOURCE_STATES,
    ) {
        // SAFETY: the barrier borrows r for this call; its union ABI has no drop glue.
        unsafe {
            list.ResourceBarrier(&[D3D12_RESOURCE_BARRIER {
                Type: D3D12_RESOURCE_BARRIER_TYPE_TRANSITION,
                Anonymous: D3D12_RESOURCE_BARRIER_0 {
                    Transition: ManuallyDrop::new(D3D12_RESOURCE_TRANSITION_BARRIER {
                        pResource: transmute_copy(r),
                        StateBefore: before,
                        StateAfter: after,
                        Subresource: D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,
                    }),
                },
                ..Default::default()
            }]);
        }
    }

    pub fn run() -> Result<()> {
        // SAFETY: descriptors, resources, allocators and lists outlive their submissions;
        // the readback is mapped only after the consumer fence and covers exactly N words.
        unsafe {
            let factory: IDXGIFactory4 = CreateDXGIFactory2(DXGI_CREATE_FACTORY_FLAGS(0))?;
            let filter = std::env::var("VICTORY_HANDOFF_ADAPTER")
                .unwrap_or_default()
                .to_lowercase();
            let mut selected = None;
            for i in 0.. {
                let Ok(a) = factory.EnumAdapters1(i) else {
                    break;
                };
                let d = a.GetDesc1()?;
                let name = String::from_utf16_lossy(&d.Description)
                    .trim_end_matches('\0')
                    .to_owned();
                if d.Flags & DXGI_ADAPTER_FLAG_SOFTWARE.0 as u32 == 0
                    && name.to_lowercase().contains(&filter)
                {
                    println!("adapter: {name}");
                    selected = Some(a);
                    break;
                }
            }
            let mut device: Option<ID3D12Device> = None;
            D3D12CreateDevice(
                &selected.with_context(|| format!("no hardware adapter matching {filter:?}"))?,
                D3D_FEATURE_LEVEL_12_0,
                &mut device,
            )?;
            let d = device.context("no D3D12 device")?;
            let queue =
                || d.CreateCommandQueue::<ID3D12CommandQueue>(&D3D12_COMMAND_QUEUE_DESC::default());
            let (producer, consumer) = (queue()?, queue()?);
            let ready: ID3D12Fence = d.CreateFence(0, D3D12_FENCE_FLAG_NONE)?;
            let used: ID3D12Fence = d.CreateFence(0, D3D12_FENCE_FLAG_NONE)?;
            let make = |texture: bool, readback: bool| -> Result<ID3D12Resource> {
                let desc = D3D12_RESOURCE_DESC {
                    Dimension: if texture {
                        D3D12_RESOURCE_DIMENSION_TEXTURE2D
                    } else {
                        D3D12_RESOURCE_DIMENSION_BUFFER
                    },
                    Width: if texture { 32 } else { (N * 4) as u64 },
                    Height: if texture { 32 } else { 1 },
                    DepthOrArraySize: 1,
                    MipLevels: 1,
                    Format: if texture {
                        DXGI_FORMAT_R32_UINT
                    } else {
                        DXGI_FORMAT_UNKNOWN
                    },
                    SampleDesc: DXGI_SAMPLE_DESC {
                        Count: 1,
                        Quality: 0,
                    },
                    Layout: if texture {
                        D3D12_TEXTURE_LAYOUT_UNKNOWN
                    } else {
                        D3D12_TEXTURE_LAYOUT_ROW_MAJOR
                    },
                    Flags: if readback {
                        D3D12_RESOURCE_FLAG_NONE
                    } else {
                        D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS
                    },
                    ..Default::default()
                };
                let mut r = None;
                d.CreateCommittedResource(
                    &D3D12_HEAP_PROPERTIES {
                        Type: if readback {
                            D3D12_HEAP_TYPE_READBACK
                        } else {
                            D3D12_HEAP_TYPE_DEFAULT
                        },
                        CreationNodeMask: 1,
                        VisibleNodeMask: 1,
                        ..Default::default()
                    },
                    D3D12_HEAP_FLAG_NONE,
                    &desc,
                    if readback {
                        D3D12_RESOURCE_STATE_COPY_DEST
                    } else {
                        D3D12_RESOURCE_STATE_COMMON
                    },
                    None,
                    &mut r,
                )?;
                r.context("resource creation")
            };
            let tex = [make(true, false)?, make(true, false)?];
            let heap: ID3D12DescriptorHeap =
                d.CreateDescriptorHeap(&D3D12_DESCRIPTOR_HEAP_DESC {
                    Type: D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV,
                    NumDescriptors: 4,
                    Flags: D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE,
                    NodeMask: 0,
                })?;
            let step =
                d.GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV) as usize;
            let cpu = |i: usize| D3D12_CPU_DESCRIPTOR_HANDLE {
                ptr: heap.GetCPUDescriptorHandleForHeapStart().ptr + i * step,
            };
            let gpu = |i: usize| D3D12_GPU_DESCRIPTOR_HANDLE {
                ptr: heap.GetGPUDescriptorHandleForHeapStart().ptr + (i * step) as u64,
            };
            for (i, t) in tex.iter().enumerate() {
                d.CreateUnorderedAccessView(t, None, None, cpu(i));
                d.CreateShaderResourceView(t, None, cpu(i + 2));
            }
            let write_code = compile(s!("produce"))?;
            let read_code = compile(s!("consume"))?;
            let root: ID3D12RootSignature = d.CreateRootSignature(0, &write_code)?;
            let pso = |bytes: &[u8]| {
                d.CreateComputePipelineState::<ID3D12PipelineState>(
                    &D3D12_COMPUTE_PIPELINE_STATE_DESC {
                        pRootSignature: transmute_copy(&root),
                        CS: D3D12_SHADER_BYTECODE {
                            pShaderBytecode: bytes.as_ptr().cast(),
                            BytecodeLength: bytes.len(),
                        },
                        ..Default::default()
                    },
                )
            };
            let (write, read) = (pso(&write_code)?, pso(&read_code)?);
            let mut keep = Vec::new();
            let mut submit = |q: &ID3D12CommandQueue,
                              pipe: &ID3D12PipelineState,
                              record: &dyn Fn(&ID3D12GraphicsCommandList)|
             -> Result<()> {
                let a: ID3D12CommandAllocator =
                    d.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)?;
                let l: ID3D12GraphicsCommandList =
                    d.CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, &a, pipe)?;
                l.SetDescriptorHeaps(&[Some(heap.clone())]);
                l.SetComputeRootSignature(&root);
                record(&l);
                l.Close()?;
                q.ExecuteCommandLists(&[Some(l.cast()?)]);
                keep.push((a, l));
                Ok(())
            };
            let paint = |l: &ID3D12GraphicsCommandList, i: usize, tag: u32| {
                transition(
                    l,
                    &tex[i],
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                );
                l.SetComputeRootDescriptorTable(0, gpu(i));
                l.SetComputeRoot32BitConstant(3, tag, 0);
                l.Dispatch(4, 4, 1);
                transition(
                    l,
                    &tex[i],
                    D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                    D3D12_RESOURCE_STATE_COMMON,
                );
            };
            let mut buffers = Vec::new();
            for _ in 0..3 {
                buffers.push((make(false, false)?, make(false, true)?));
            }
            let sample = |l: &ID3D12GraphicsCommandList, t: usize, b: usize| {
                let (out, rb) = &buffers[b];
                transition(
                    l,
                    &tex[t],
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,
                );
                transition(
                    l,
                    out,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                );
                l.SetComputeRootDescriptorTable(1, gpu(t + 2));
                l.SetComputeRootUnorderedAccessView(2, out.GetGPUVirtualAddress());
                l.Dispatch(4, 4, 1);
                transition(
                    l,
                    out,
                    D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                    D3D12_RESOURCE_STATE_COPY_SOURCE,
                );
                l.CopyResource(rb, out);
                transition(
                    l,
                    &tex[t],
                    D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,
                    D3D12_RESOURCE_STATE_COMMON,
                );
            };
            submit(&producer, &write, &|l| {
                paint(l, 0, OLD);
                paint(l, 1, DECOY)
            })?;
            producer.Signal(&ready, 1)?;
            consumer.Wait(&ready, 1)?;
            submit(&consumer, &read, &|l| sample(l, 0, 0))?;
            consumer.Signal(&used, 1)?;
            // Submit the future wait before the producer. It must not block the submitting CPU.
            consumer.Wait(&ready, 2)?;
            submit(&consumer, &read, &|l| {
                sample(l, 0, 1);
                sample(l, 1, 2)
            })?;
            consumer.Signal(&used, 2)?;
            producer.Wait(&used, 1)?;
            submit(&producer, &write, &|l| paint(l, 0, NEW))?;
            producer.Signal(&ready, 2)?;
            let start = Instant::now();
            while used.GetCompletedValue() < 2 {
                d.GetDeviceRemovedReason()?;
                ensure!(
                    start.elapsed() < Duration::from_secs(5),
                    "timed out waiting for the GPU"
                );
                std::thread::sleep(Duration::from_millis(1));
            }
            d.GetDeviceRemovedReason()?;
            for ((name, tag), (_, rb)) in [
                ("right / before", OLD),
                ("right / after", NEW),
                ("wrong / after", DECOY),
            ]
            .into_iter()
            .zip(buffers.iter())
            {
                let mut p = ptr::null_mut();
                rb.Map(0, None, Some(&mut p))?;
                let vals = slice::from_raw_parts(p.cast::<u32>(), N);
                let diff = |v: u32| {
                    vals.iter()
                        .enumerate()
                        .filter(|(i, x)| **x != v + *i as u32)
                        .count()
                };
                let (own, current) = (diff(tag), diff(NEW));
                println!(
                    "{name}: first={:#010x} last={:#010x} mismatches(expected)={own}/{N} mismatches(new)={current}/{N}",
                    vals[0],
                    vals[N - 1]
                );
                rb.Unmap(0, None);
                ensure!(
                    own == 0 && current == if tag == NEW { 0 } else { N },
                    "incorrect texture handoff"
                );
            }
            Ok(())
        }
    }
}
