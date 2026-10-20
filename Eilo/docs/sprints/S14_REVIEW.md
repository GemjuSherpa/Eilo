# S14 — visual conversation implementation

S14 proceeds independently of the outstanding S08 physical feasibility decision. Storage, recall and persistent memory remain disabled/dependency-blocked. Task branches consolidate into one final sprint PR after all available independent work is verified.

## VC-VIS-01 — controller-driven ripple

Home now renders blue/lavender rounded decoration from the existing native metadata snapshot. Only listening and speaking animate; thinking, standby, stopped, pending capture and unavailable/error states remain distinct through shape and the existing live state label. The decoration is hidden from accessibility traversal; Start/Stop remains separate and accessible. It starts no capture, inference or playback. Stop and state replacement reset the animation; background and reduced motion freeze it. Unknown motion preference defaults to static, and a late preference query cannot override a newer accessibility event.

Validation: 21 mobile tests, TypeScript and ESLint pass; every controller state, pending capture, error, Stop, background, reduced motion and a stale accessibility query are covered. 309 Swift tests, normal simulator build/install and three fresh ten-second launches pass (s14-ripple). These are implementation/regression results, not physical visual, VoiceOver or TalkBack acceptance.

VC-VIS-03 needs a separate bounded volatile spoken-content channel: the existing state contract intentionally forbids text and must retain that boundary. Full joined native speech, physical visual/accessibility acceptance and unsupported background operation are not inferred from this change.

## VC-VIS-02 — motion, theme and scalable layout

The initial ripple cycle is one second, with a bounded 500–4000 ms design parameter and safe fallback for non-finite/out-of-range values. Existing blue/lavender light/dark semantic colors meet measured 4.5:1 normal-text and 3:1 control-boundary checks. Long action text wraps without fixed height or font-scaling caps; touch dimensions remain at least 48 points. Reduced-motion and background behavior remain covered.

Actual simulator rendering exposed two integration issues missed by process-only launch checks: Metro could not index the reused external dependencies, and the fixed navigation heading clipped at maximum accessibility text size. Metro now indexes the actual dependency root and maps workspace packages to this checkout. Headings scroll with content, top safe areas remain protected, and native navigation owns the iOS status-bar style using the matching Info.plist setting. Light/default-size and dark/maximum-size actual Home screenshots were inspected. No Simulator GUI component is installed in the operator-updated Xcode; scroll/touch exploration and VoiceOver/TalkBack acceptance remain NOT_RUN. The temporary synthetic simulator consent file and theme/text-size settings were restored after inspection. No physical-phone setting or audio control was used.

Validation: 25 mobile tests, TypeScript and ESLint pass; 309 Swift tests, normal simulator build/install and three fresh ten-second launches pass on the final configuration (s14-accessibility-native). Actual Metro bundling and Home rendering passed after the resolution fix; launch-process survival alone is not treated as visual acceptance.
