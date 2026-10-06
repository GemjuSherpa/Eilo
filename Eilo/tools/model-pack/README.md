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
