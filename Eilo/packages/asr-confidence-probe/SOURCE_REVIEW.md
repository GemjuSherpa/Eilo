# Pinned source review

User approved the additional 35 MiB source-only inventory after the full archive stopped at its original 50 MiB cap. All 696 files (30,224,667 bytes) matched the immutable Git tree blob hashes and lengths. No runtime binaries, standalone model assets or audio were downloaded. Source remains in ignored local cache.

The custom CMake target compiles only streaming-model, contextual-biaser (unused), tokenizer, utility and ORT utility sources. These are covered by the repository MIT license; the bundled ORT headers are MIT. Both complete notices are retained here. Existing English streaming weights remain covered by the upstream MIT default. No TTS/data, Eigen/MPL2, fbank/Apache, kissfft/BSD, UTF8proc or UTF-8 sources are compiled by this target. The source inventory retains their available license files for inspection. No prototype binary is distributed. Full shipping third-party inventory remains a separate gate.

The target uses existing NDK27.1.12297006 and existing ORT1.23.2. It does not run upstream CMake/download scripts or fetch dependencies. The first minimal Android link succeeded with no additional source/dependencies. The SDK embedded VAD header was fetched within the explicit approval but is not compiled by this ASR-only target.
