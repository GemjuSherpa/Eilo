# Native persona policy evaluation

VC-BEHAV-01 supplies fixed, versioned native system rules for honest AI identity, brief supportive replies, acknowledgment of expressed feelings, avoidance of diagnosis/exclusivity/secrecy pressure, and respect for ending a conversation. Kotlin and Swift consume the same frozen review contract. User/history text cannot replace the privileged system turn; the Qwen non-thinking template and existing budgets remain mandatory.

This is prompt configuration and a review harness, not a semantic safety classifier. No ordinary model caller, speech release, history write or model-readiness bypass is enabled. VC-BEHAV-02/03/04 and the joined turn remain separate work.

`tests/persona-fixtures.json` freezes the rules, six core cases, three paraphrased cases and Gemju Sherpa's rubric. Exact reference wording is marked; successful reference cases alone cannot establish generalization. Initial/refinement/example trial reports retain observed defects. The current report contains bounded generic model outputs, null ratings and pending-review status. Those outputs are never speech-approved.

Reproduce with the existing pinned local assets/toolchain, from the repository root:

```sh
python3 Eilo/packages/persona-policy/check_ios.py --udid <existing-booted-simulator>
```

The evaluator checks the pinned source, links the native runtime, uses a synthetic signed evaluation pack and a controller-owned worker, renders the actual native prompt and collects at most 96 tokens per case through the non-thinking UTF-8 guard. Temporary pack files are explicitly removed. Nothing is downloaded, no microphone is opened and nothing is released to speech. The report is written only after all cases complete. Simulator OS-wide network isolation and physical inference are unverified.

The standard native suites check the frozen policy/template boundary and trimming; the official Jinja golden check remains in `packages/llm-runtime/check_template.py`. The app retains its unavailable model gate. Gemju Sherpa reviews candidate honesty, support, autonomy and brevity; automated compiler/fixture success cannot supply those ratings.
