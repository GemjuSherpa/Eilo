# S03 — Model preparation and verified installation

Gemju Sherpa approved S02 and authorized S03 on 6 October 2026. Task branches merge into sprint/s03-model-packs before main. Review remains pending for S03. No release, production hosting, paid services or later sprint is included.

Local models and isolated conversion tools remain ignored by Git. Native installer has no personal-data inputs. Production release trust keys and a hosting origin are not provisioned.

- VC-PACK-01 (task/s03-vc-pack-01): Official pinned source hashes verified; BF16 conversion executed and GGUF inventory/tokenizer/template inspected. 4,069,679,360 bytes, SHA-256 2fd1d807958fc7352aa39b9d94a04073aa04ee07a735f272876a4b3ee90ac48f. Desktop RAM measured separately; phone inference not tested.

- VC-PACK-02 (task/s03-vc-pack-02): Pinned Q4_K_M quantizer executed twice; cmp exit 0 and equal SHA-256 c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120. Each output is 1,282,439,424 bytes. GGUF quantization metadata and unchanged tokenizer/template inspected.

- VC-PACK-10 (task/s03-vc-pack-10): Distribution privacy review completed: official Hugging Face policy reviewed; no production origin/CDN configuration or no-access-history evidence exists. Release remains fail-closed with empty trust/origin/license approval. BLOCKED: Production hosting has no verified logging/retention configuration; provider selection and infrastructure authorization are required before release.

- VC-PACK-03 (task/s03-vc-pack-03): Bounded strict native manifest schema; compiler and malformed/duplicate/path/runtime/platform tests passed on Kotlin and Swift. See docs/models/MANIFEST.md; final native suites45 each. Android platform parser/device evidence remains unverified.

- VC-PACK-04 (task/s03-vc-pack-04): ES256 exact-byte signature verification uses configured native trust. Valid/tampered/unknown-key/algorithm/empty-trust and shared OpenSSL interoperability fixtures pass. Default production trust remains empty.

- VC-PACK-05 (task/s03-vc-pack-05): Isolated default-trust HTTPS streaming transport, bounded bytes, no cookies/auth/cache/automatic redirects; synthetic server request/foreign-redirect/cancellation/response tests pass. Real CDN traffic audit is not run.

- VC-PACK-06 (task/s03-vc-pack-06): Streaming SHA-256 and exact length verification; truncation, bit-flip, oversize, symlink and cancellation tests pass. No corrupt or partial artifact obtains proof.

- VC-PACK-07 (task/s03-vc-pack-07): Checkpoint binds manifest digest/index/strong ETag. Injected interruption safely resumes or restarts on changed ETag/checkpoint; complete file always rehashed. Real device process-kill not run.

- VC-PACK-08 (task/s03-vc-pack-08): Whole-pack immutable version directories and atomic synced pointer; startup signature/hash checks; failure-boundary/stale-proof/rollback/corruption/license/trust tests pass. Physical power-loss/filesystem/backup tests not run.

- VC-PACK-09 (task/s03-vc-pack-09): Native readiness blocks permission/capture/output without valid assets/configuration/offline voice; races and activation cache invalidation tested. Metadata-only modelStatus validated by TypeScript; real speech runtimes remain later work.

## Combined verification

Local final checks passed on 6 October 2026:

- `npm --prefix Eilo run lint`, `npm --prefix Eilo run typecheck`, `npm --prefix Eilo test`: 34 tests (mobile UI1, contracts33).
- JDK17/Android SDK: Gradle `:app:compileDebugKotlin :app:testDebugUnitTest`, then `:app:assembleDebug :app:assembleRelease :app:testDebugUnitTest --max-workers=2`: 45 JUnit tests, debug/release builds passed. Android release is template test-signed, not a distribution build.
- `swift test --package-path Eilo/packages/native-test-seam`: 45 XCTest tests passed. Swift package name is historical; production installer/controller sources compile directly in the app target.
- `xcrun --sdk iphonesimulator swiftc -typecheck -target arm64-apple-ios18.0-simulator Eilo/packages/native-test-seam/Sources/NativeTestSeam/*.swift`: passed.
- Xcode `Release`, `iphonesimulator`, generic simulator destination, `CODE_SIGNING_ALLOWED=NO`, `build/S03` derived data: actual app target BUILD SUCCEEDED.
- Official input Git blob/LFS hashes all matched. BF16 conversion and two independent Q4_K_M quantizations executed; repeat output is byte-identical. Source/output tensor count, vocabulary size and chat-template hashes match. Exact evidence is in docs/models/evidence.

Final review also made verified Kotlin manifest collections immutable, prevented stale readiness refresh from overriding invalidation, rechecked token identity after adapter status reads and verified the same OpenSSL ES256 wire-format vector in Kotlin and Swift. The temporary synthetic private key was deleted; only public signature data is recorded.

## Review boundaries

VC-PACK-01/02 have passed local build-artifact verification; native tasks have implementation and synthetic compiler/unit evidence, with physical/integrated evidence partial. VC-PACK-10 has a completed blocking review: production origin/CDN logs/retention are unverified. Review is pending from Gemju Sherpa; no S03 approval, production hosting or release readiness is recorded.

Not run: phone inference/quality/latency/thermal/battery/RAM, real model adapters and installed offline voices, actual CDN packet/log inspection, physical permission/background/backup/transfer tests, abrupt process death/power-loss durability and Android platform parser/crypto instrumentation. Simulated failure injections are not physical crash results. No shipping key, approved complete model pack or provider configuration exists. Python/CMake conversion tools are build-only. Core capture remains disabled by missing production readiness/adapters.

Installer calls perform blocking IO on a dedicated installer worker. Later runtime integration must refresh/invalidate native readiness on asset/configuration changes and verify files on loading; status checks themselves do no expensive IO. Old version directories are retained for recovery; generic model disk cleanup/quota policy and full runtime/transitive license inventory need follow-up before release. No model binaries, credentials or personal test data are committed or uploaded.

S02 approval is recorded separately without upgrading its physical/later-integration evidence. Gemju Sherpa's existing S02 review-document edit and .DS_Store change are preserved outside this work's commits.
