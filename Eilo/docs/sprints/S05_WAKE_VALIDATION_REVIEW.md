# S05 — Wake acceptance fixture validation

VC-TURN-02 / F03 / A02 follow-up. Gemju Sherpa merged PR #27 at main af5e916. This change starts from that reviewed main on sprint/s05-wake-validation, with task/s05-vc-turn-02-validation as its task branch. It fixes evaluation behavior; the wake adapter remains partial.

## Failure and correction

The host evaluation iterated arbitrary fixture entries and treated every unrecognized kind as an unscored diagnostic. Empty, diagnostic-only or accidentally misspelled acceptance sets could therefore report a pass without testing wake and ordinary speech. Validation now runs before candidate integrity checks, compiler invocation or scoring. Require both wake and nonwake cases, allow only the two explicitly named diagnostic classes, bound the set to 256 entries, require unique local WAV filenames and valid SHA256 metadata. Reject directory traversal and absolute paths. Identical hashes across distinct files remain eligible because the frozen set contains real duplicate TTS outputs; reports expose total and unique audio counts rather than imply independent samples.

The archived result includes the new counts. No candidate thresholds, expected labels, hashes, phrase, pronunciation, mobile readiness or audio wiring are changed.

## Checks and limitations

- Python compiler check and eight synthetic validation tests: PASS in normal and optimized Python modes. New cases cover empty/one-sided/diagnostic-only suites, misspelled labels, malformed metadata, duplicate/escaping filenames and the set bound. Hosted JavaScript checks now run these tests without downloading models or generated audio.
- Pinned archive/extracted-file/fixture checks and C++17 warnings-as-errors compilation: PASS. Scripted C ABI contract with AddressSanitizer/UndefinedBehaviorSanitizer: PASS.
- Actual local CPU keyword evaluation: exit 1, acoustic acceptance FAIL, exactly the previous two target misses and one nonwake activation. 20 fixture entries / 18 unique WAV hashes; seven wake entries, eleven nonwake entries, two diagnostic controls. One synthetic TTS voice, not a representative speaker/noise dataset or calibrated accuracy measure.
- Unsigned Debug build on the same iPhone 18 Pro / iOS 27.0 simulator: PASS before commit. Live launch checks are recorded below after installation.
- Physical-phone recognition, mobile runtime integration, vendor buffer lifetime, artifact trust/distribution rights and conversation tests remain unverified. VC-TURN-03 remains dependency-blocked. Simulator startup is not acoustic acceptance.

## Reproduce

From Eilo, run `python3 packages/wake-runtime/test_fixture_validation.py` and repeat with `python3 -O`. With the previously pinned local candidate assets and frozen fixtures, run `python3 packages/wake-runtime/check_host.py`; current expected exit is 1 and the three failures remain explicit. No raw recordings or generated WAVs are published. See the wake-runtime README for asset provenance and reproduction limitations.

Review scope: prevent false acceptance from invalid fixture sets and expose duplicate-audio counts. Main merge awaits Gemju Sherpa review. Unrelated S02_REVIEW.md edits are preserved.

Live pre-commit check: installed the freshly built Debug app and ran `python3 -O scripts/verify-ios-launch.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8 --dwell 10`: three fresh launches PASS after ten seconds each. No simulator erase, consent change or microphone capture. Staged diff and secret scans follow before commit; hosted checks await publication.
