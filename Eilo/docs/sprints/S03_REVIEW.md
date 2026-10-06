# S03 — Model preparation and verified installation

Gemju Sherpa approved S02 and authorized S03 on 6 October 2026. Task branches merge into sprint/s03-model-packs before main. Review remains pending for S03. No release, production hosting, paid services or later sprint is included.

Local models and isolated conversion tools remain ignored by Git. Native installer has no personal-data inputs. Production release trust keys and a hosting origin are not provisioned.

- VC-PACK-01 (task/s03-vc-pack-01): Official pinned source hashes verified; BF16 conversion executed and GGUF inventory/tokenizer/template inspected. 4,069,679,360 bytes, SHA-256 2fd1d807958fc7352aa39b9d94a04073aa04ee07a735f272876a4b3ee90ac48f. Desktop RAM measured separately; phone inference not tested.

- VC-PACK-02 (task/s03-vc-pack-02): Pinned Q4_K_M quantizer executed twice; cmp exit 0 and equal SHA-256 c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120. Each output is 1,282,439,424 bytes. GGUF quantization metadata and unchanged tokenizer/template inspected.

- VC-PACK-10 (task/s03-vc-pack-10): Distribution privacy review completed: official Hugging Face policy reviewed; no production origin/CDN configuration or no-access-history evidence exists. Release remains fail-closed with empty trust/origin/license approval. BLOCKED: Production hosting has no verified logging/retention configuration; provider selection and infrastructure authorization are required before release.
