# iOS key authentication API compatibility

The strict joined speech compile exposed the deprecated kSecUseOperationPrompt query key in
the S09 provider. Apple's installed SDK marks it deprecated since iOS14 and prescribes an
LAContext with localizedReason. That property is available since iOS11, below Eilo's iOS18 floor.

`task/ios-key-authentication-context` replaces that query entry with the same reason on the
existing context. It retains user-presence/passcode protection, no-authentication-reuse setting,
authentication-context query, availability predicates, cancellation and post-read validation.
No keychain operation is run by this change's tests; normal provider construction remains denied.
No production caller, storage, trust key or microphone activation is introduced.

`task/ios-key-strict-build-evidence` adds strict device and simulator typechecks of every native
Swift source to the foundation iOS CI job. The joined evaluator also includes every native source
again; its temporary protected-key exclusion is removed. There is no warning suppression.
Both tasks consolidate into `sprint/ios-key-authentication-compatibility` for one final PR.

## Verification and scope

- All native Swift sources typecheck for arm64 iOS18 device and simulator with warnings as errors.
- The real eight-case signed VAD/ASR installer simulator evaluation passes on the updated source.
  Its aggregate report and shared source/report pins are refreshed. Existing host-JNI evidence is
  retained without claiming a new Android native-model run; Android production sources are unchanged.
- A fresh full-source joined evaluation executes real signed VAD/ASR -> CPU generation -> SDK speech,
  two turns with 16/48kHz input and bounded context, then quiet input with no reply/model start.
- Normal 306 Swift tests, normal app builds/installs and three fresh ten-second simulator launches
  before each code-task commit (six total). Workspace lint/typecheck/9mobile/33contract tests and
  normal/optimized synthetic evidence validation remain green. Secret scans precede publication.
- Historical S09_VALIDATION and the PR75 review remain unchanged as records of their original
  builds. This record and refreshed current runtime evidence describe the new compatibility change.

Actual physical OS authentication, keychain cancellation and hardware security are still NOT_RUN.
Compile success is not authentication acceptance. The pending physical foreground-trial approval
and device developer-image readiness are separate. S08 HOLD, persistent memory denial, S10/S11
entry blockers and production defaults remain unchanged. Merge only after all hosted tests pass
under the user's explicit continuation authorization; do not bypass review/branch restrictions.
