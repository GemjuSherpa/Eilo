# S14 — visual conversation implementation

S14 proceeds independently of the outstanding S08 physical feasibility decision. Storage, recall and persistent memory remain disabled/dependency-blocked. Task branches consolidate into one final sprint PR after all available independent work is verified.

## VC-VIS-01 — controller-driven ripple

Home now renders blue/lavender rounded decoration from the existing native metadata snapshot. Only listening and speaking animate; thinking, standby, stopped, pending capture and unavailable/error states remain distinct through shape and the existing live state label. The decoration is hidden from accessibility traversal; Start/Stop remains separate and accessible. It starts no capture, inference or playback. Stop and state replacement reset the animation; background and reduced motion freeze it. Unknown motion preference defaults to static, and a late preference query cannot override a newer accessibility event.

Validation: 21 mobile tests, TypeScript and ESLint pass; every controller state, pending capture, error, Stop, background, reduced motion and a stale accessibility query are covered. 309 Swift tests, normal simulator build/install and three fresh ten-second launches pass (s14-ripple). These are implementation/regression results, not physical visual, VoiceOver or TalkBack acceptance.

VC-VIS-03 needs a separate bounded volatile spoken-content channel: the existing state contract intentionally forbids text and must retain that boundary. Full joined native speech, physical visual/accessibility acceptance and unsupported background operation are not inferred from this change.
