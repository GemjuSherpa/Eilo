# S05 physical trials

Gemju Sherpa connected an iPhone17 Pro Max and reported iOS26.6.1. Xcode recognizes the physical model. A selected signing team permits local development builds; it does not establish wake, ASR, background or latency results. Physical Android hardware is unavailable.

## Connect and run

1. Connect the phone to the Mac by USB, unlock it, and accept Trust on the phone. Enable Developer Mode if Xcode requests it; follow the phone's restart/confirmation steps.
2. Open `apps/mobile/ios/Eilo.xcworkspace` in Xcode. Use the workspace to include CocoaPods dependencies.
3. Click the blue Eilo project icon in the left sidebar, select Eilo under TARGETS, then Signing & Capabilities. Enable Automatically manage signing and choose the free personal Team added through Xcode → Settings → Accounts. Account credentials and signing profiles stay local.
4. Select the physical phone in the scheme destination selector beside Eilo. Click Run. If Xcode requests device trust, unlock the phone and finish that prompt. A free development profile may require periodic renewal; store distribution is a separate process.
5. For Debug, start Metro from the workspace (`npm start`). The phone must reach the Mac's development server; a signed Release build bundles JS and is the useful offline-launch check. Developer server connectivity is not a core inference dependency.
6. Normal Eilo remains in model setup until verified production packs/offline voices are ready. File-decoding evaluation results do not enable the microphone or bypass consent. Never report an unavailable Start as a successful voice trial.

## Frozen wake protocol (VC-TURN-09)

Freeze model/checkpoint/keyword lexicon/threshold/boost, native revision and labelled dataset hashes before running. Use the existing frozen synthetic positive/nonwake clips for quiet playback trials; system-generated voice audio stays local. Report separately for the phone speaker, wired headphones if available and Bluetooth headphones if available. Record supported actual routes instead of inventing absent accessories. Keep room noise, playback level/distance, phone orientation, cold/warm condition and trial count in the reproducibility record; do not record people or collect real-user audio.

Count each labelled wake phrase once: correct detections, missed positives, unexpected multiple detections and nonwake activation events. Run the frozen nonwake ambient playback set for eight measured hours per declared route. The eight-hour dataset and a verified physical capture/evaluation attachment are currently unavailable. Do not multiply a short synthetic file count into an eight-hour result. Count-only live events must stay local and contain no audio/transcript/user identifiers. A connected phone alone is not the completion of this task.

Persist only device model/OS, route, candidate revision/settings, dataset digest, measured elapsed seconds and aggregate labelled/activation counts. Calculate detection rate with its denominator and false activations per measured hour. Use null/NOT RUN when missing. Preserve failed counts when retuning, freeze a new version, and repeat the same trial. The generated `packages/wake-runtime/tests/wake-trial-summary.json` distinguishes the current synthetic score from these absent physical measurements.

## ASR and interruption protocol (VC-TURN-08/10)

Use frozen synthetic English references with separate accent/name/number/noise slices. Report final word error rate, substitutions/deletions/insertions and sample/reference-word counts. Number formatting normalization must be frozen before testing; do not silently repair the current name error. The initial installed US-English synthetic voice provides no accent diversity evidence.

Measure physical confirmed-speech onset to actual last audible output across at least30 speaker/headphone interruptions, including short noise bursts and Eilo's own playback. Record aggregate latency median/p95, success/miss counts, route and warm/cold conditions; retain no personal speech or transcript. The300 ms p95 target includes capture scheduling, native classification, queued output cancellation and hardware tail. Unit-test sample clocks do not measure this latency.

The conservative output gate currently suppresses microphone recognition during app output. Full duplex barge-in requires separately verified echo-separated user speech; a VAD probability alone cannot distinguish Eilo's voice from a person. Until that route is verified, do not label self-playback rejection or barge-in as a physical pass. Platform TTS/offline voice wiring and production turn attachment remain dependencies.
