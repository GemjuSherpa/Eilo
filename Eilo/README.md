# Eilo development workspace

This directory contains the React Native app, shared packages, native fixtures and model tooling.

See the [project README](../README.md) for current implementation status, architecture, technology compatibility, setup, reproduction commands, development workflow and outstanding constraints.

Run JavaScript workspace commands from this directory:

```sh
npm ci --no-audit --no-fund
npm run lint
npm run typecheck
npm test
npm start
```

The current foundation is not a complete voice conversation. Native production model readiness remains unavailable; physical-device and background feasibility remain unverified. Use the project README and sprint evidence for the exact checkpoint results.

The iOS exposed-reference ASR replay has an aggregate-only report and deterministic CI checks in `packages/asr-ios-corpus`. Its previously exposed Common Voice and correlated-noise observations are diagnostic only; they do not establish calibration or authorize a score threshold. See [`docs/sprints/S05_IOS_REFERENCE_DIAGNOSTICS.md`](docs/sprints/S05_IOS_REFERENCE_DIAGNOSTICS.md).
