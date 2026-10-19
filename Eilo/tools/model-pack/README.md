# Reproduce the model conversion

Build tools are local Python/C++, not mobile runtime dependencies. Official inputs are pinned in source-lock.json. All downloaded files were verified against the official commit's Git blob or LFS SHA-256 before conversion. Binary sources/weights/output remain in ignored .local/model-build; do not commit them.

Working directory: Eilo. Create a Python 3.12 virtual environment in .local/model-build/venv and install build-requirements.lock from reputable package registries. Download the official Qwen snapshot by model_revision and the official llama.cpp archive by llama_cpp_revision. Unpack the latter into .local/model-build/llama.cpp; verify the source hashes in docs/models/evidence/source-hashes.json and archive hash in source-lock.json before running tools.

```sh
.local/model-build/venv/bin/cmake -S .local/model-build/llama.cpp -B .local/model-build/llama.cpp/build -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=OFF -DGGML_OPENMP=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_CURL=OFF
.local/model-build/venv/bin/cmake --build .local/model-build/llama.cpp/build --target llama-quantize -j 3
.local/model-build/venv/bin/python .local/model-build/llama.cpp/convert_hf_to_gguf.py .local/model-build/qwen --outtype bf16 --outfile .local/model-build/qwen3-1.7b-bf16.gguf
.local/model-build/venv/bin/python tools/model-pack/inspect_gguf.py .local/model-build/qwen3-1.7b-bf16.gguf --llama-source .local/model-build/llama.cpp --output docs/models/evidence/bf16.json
```

VC-PACK-01 passed locally: Qwen3 architecture, 311 BF16/F32 tensors, GPT-2 tokenizer with 151936 entries, preserved chat template. Template supports enable_thinking; S06 must actually set it false through the runtime template configuration. No inference/quality/phone RAM test was performed. Desktop conversion took 160.20 seconds with 2,570,354,688 bytes maximum resident memory on a 16 GiB Mac. Large-file transfers were interrupted and safely restarted/resumed; final complete source hashes all match official provenance.

Weights: official Qwen Apache-2.0 license; converter/runtime source: llama.cpp MIT. License texts are in docs/models/licenses. Complete mobile runtime/ASR/wake/VAD/system-voice and transitive inventory remains a release gate; these are evaluation artifacts, not an approved shipping pack.

## Q4_K_M conversion (VC-PACK-02)

```sh
.local/model-build/llama.cpp/build/bin/llama-quantize .local/model-build/qwen3-1.7b-bf16.gguf .local/model-build/qwen3-1.7b-q4-k-m.gguf Q4_K_M 2
.local/model-build/llama.cpp/build/bin/llama-quantize .local/model-build/qwen3-1.7b-bf16.gguf .local/model-build/qwen3-1.7b-q4-k-m-repeat.gguf Q4_K_M 2
cmp .local/model-build/qwen3-1.7b-q4-k-m.gguf .local/model-build/qwen3-1.7b-q4-k-m-repeat.gguf
.local/model-build/venv/bin/python tools/model-pack/inspect_gguf.py .local/model-build/qwen3-1.7b-q4-k-m.gguf --llama-source .local/model-build/llama.cpp --output docs/models/evidence/q4-k-m.json
```

Independent repeat evidence is recorded after both executions complete, not inferred from a recipe.

VC-PACK-02 passed locally: both outputs are byte-identical, 1,282,439,424 bytes; SHA-256 c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120. File type 15 (Q4_K_M), 311 tensors (F32/Q4_K/Q6_K); tokenizer/template match BF16 exactly. No reply quality or mobile RAM/latency result is claimed.


### CPU comparison source preparation

`qwen3-0.6b-source-lock.json` pins the official Apache-2.0 BF16 source snapshot
for VC-LLM-06. The selected files total 1,519,193,708 bytes. No weights are
committed. The official GGUF repository currently provides Q8_0; the comparison
requires a local BF16 → Q4_K_M conversion with verified converter provenance,
followed by an independent repeat quantization and output hashes.

Run `python3 tools/model-pack/fetch_comparison_source.py` to print the plan
without network access. Only after explicit operator download approval, use
`--download-approved --destination .local/model-build/qwen3-0.6b-source`.
`--verify-only --destination PATH` checks an existing snapshot without network.
The helper checks the pinned byte size and LFS SHA-256 or Git blob SHA-1, streams
into a temporary file, removes failed transfers, rejects existing symlinks and
corrupt files, and publishes without replacing existing files. It does not
resume partial downloads. Allow about 5 GB for source and conversion outputs.

Download approval and actual conversion/device results are still pending.
This preparation does not change `physical-model-comparison.json` or accept
any S08 physical, network, quality, or memory gate. Each candidate must run in
a fresh app process: the Mach footprint peak is a process-lifetime high-water
mark and cannot be reset between models. Fixed synthetic prompts only; human
quality ratings and independent traffic observation remain separate evidence.
