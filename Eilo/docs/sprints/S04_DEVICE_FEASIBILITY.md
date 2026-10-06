# S04 physical audio feasibility — pending review

Gemju Sherpa has reported no Android phone. An earlier local inventory reported no physical device; the final refresh timed out initializing CoreDeviceService. Current physical-device availability is therefore unverified. The previously supplied iOS version is insufficient to identify the device model or RAM. No physical-device row below was executed. Synthetic policy/controller tests and unsigned simulator builds establish different evidence and do not establish feasibility.

## Required matrix

For each platform, record model, RAM, OS/build, battery state, permission state, headphones/route and test build revision. Use synthetic content. Record actual mic indicators, native state, capture release, stale-event rejection, elapsed Stop time and any unexpected output. Do not record personal audio in evidence.

| Scenario | Android | iOS | Required result |
| --- | --- | --- | --- |
| Fresh install / launch / process restart | NOT RUN | NOT RUN | No permission prompt or capture until explicit Start |
| Permission denied / revoked during capture | NOT RUN | NOT RUN | Stopped, released mic, rejected delayed work |
| Foreground Start / Stop, native output volume | NOT RUN | NOT RUN | Correct indicator and release; gain does not change consent |
| UI suspended / detached | NOT RUN | NOT RUN | Native authority survives; metadata reconnect is truthful |
| Background choice off / on after authentication | NOT RUN | NOT RUN | Off stops; no automatic Start from consent |
| Home/background with an active capture | NOT RUN | NOT RUN | Android requires existing service + consent + unlock; iOS stops |
| Screen lock / protected data unavailable | NOT RUN | NOT RUN | Stop; no locked capture, speech or personal writes |
| Call / audio focus or session interruption | NOT RUN | NOT RUN | Stop; interruption end cannot resume |
| Headphones / Bluetooth removal and reconnection | NOT RUN | NOT RUN | Stop; explicit unlocked speaker confirmation needed |
| Service/process killed / task removed / reboot | NOT RUN | NOT RUN | No resurrection or automatic capture |
| Extended background / battery restrictions / Android Doze | NOT RUN | NOT RUN | Observe actual platform limits; no keepalive workaround |
| Device authentication canceled / denied / app exits | NOT RUN | NOT RUN | No changed background consent or automatic capture |
| TalkBack / VoiceOver, large text and target size | NOT RUN | NOT RUN | Understandable choice/state and usable Stop/volume controls |

## Android decision (VC-AUDIO-09)

Foreground microphone service is non-sticky, unexported and process-owned, with generic notification Stop. Unlocked background eligibility needs independently authenticated consent and an already-running service. New capture still starts only from the foreground. Activity destruction deliberately stops and releases capture; reconnect does not revive it. Locking closes capture eligibility. No locked listening or speech exception is implemented.

Actual OEM lifecycle, notification tap, microphone indicator, resource release timing and long-run restrictions remain unknown. No Android supported-device or locked-audio feasibility pass is claimed. Later pipeline model readiness is also required for an end-to-end production capture trial; do not inject test readiness into a shipping build.

## Deferred acceptance

VC-AUDIO-06, VC-AUDIO-09 and VC-AUDIO-10 remain blocked for their background/physical acceptance. Neither locked speech nor sustained background feasibility is delivered by S04. All extended screen-off/standby gates in later sprints remain pending. Device evidence and review are required before treating these tasks as verified.
