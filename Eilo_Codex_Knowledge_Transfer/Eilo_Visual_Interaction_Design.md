# Eilo Visual Interaction Design

Version 2.0 | 5 October 2026 | Change CR-2026-10-05-01

The owner instructed that the independent ripple and visual-results exploration be finalized and merged into Eilo. This is the current design and requirements baseline. It supersedes the warm-neutral/teal Home treatment, the static-only wave, the absence of live-result display and the earlier prohibition on all online search. It does not replace local inference with cloud inference or authorize conversation-history upload. Native implementation, external provider selection and device evidence remain outstanding.

## 1 Product layout

Home uses a soft blue/light-purple gradient, a round wave originating at the exact visual centre and quiet navigation. During active listening and spoken output, smooth rings expand and fade at the edges. A one-second seamless loop is the requested animation preview and initial tunable motion parameter, not a proven production comfort or battery setting. Stopped shows a static central Start control; standby has an explicit wake status and no listening animation; thinking has a distinct processing status. Animation never substitutes for honest capture state.

The minimal appearance retains an accessible Start/Stop target, labelled controller state, current privacy mode and Home/Memory/Settings access. iOS uses platform tab and sheet conventions; Android uses its navigation bar, Back behavior and native service controls. The two-icon exploratory drawing was illustrative: authenticated Memory cannot become inaccessible. Place account options inside Settings. No mandatory chat composer, conversation list, advertising or human avatar is introduced.

## 2 Colour and motion system

| Role | Light | Dark |
|---|---|---|
| Gradient start | #DCEEFF | #101A30 |
| Gradient end | #E8DEFF | #241B3D |
| Surface | #FFFFFF | #18233B |
| Primary action | #2453C6 | #B8CBFF |
| Text | #172642 | #F1F4FF |
| Secondary text | #43516A | #C3CDE3 |
| Essential boundary | #66748B | #91A4C7 |
| Error | #B42335 | #FFADB7 |
| Warning | #805600 | #F2D080 |

Gradients and translucent ripples are decoration. All readable text and essential controls sit on stable surfaces, with measured contrast across every actual background. Use system fonts, existing spacing roles and text scaling. Preserve minimum 48-logical-unit shared touch regions and 8-unit separation. Do not assume the old 22 contrast checks apply to this palette. Dark mode, high contrast, VoiceOver/TalkBack and enlarged text require fresh verification.

Reduced motion replaces rings with a static mark and a plain state label. Never flash brightness or animate the entire text/result sheet repeatedly. Pause rendering while the surface is hidden, except separately permitted native surfaces; no offscreen animation loop is a background keepalive. Motion is not computed from raw microphone samples merely to decorate the screen.

## 3 Display preferences

Voice always remains the normal conversational output unless the user explicitly changes audio settings. Visual options control what accompanies it. Recommended initial defaults are Text on, Images off, Videos off. These defaults are assumptions, not previous owner selections.

Voice only is a mutually exclusive visual mode: enabling it turns off all visual response cards without muting Eilo and remembers prior text/image/video selections for restoration. Individual types can otherwise be independently enabled. Settings and current-session controls offer labelled switches; commands such as “show text,” “show pictures,” “voice only” and “hide this” work only during an already-authorized active conversation. Ambient speech cannot change them. Persistent privacy/permission changes still require the established unlocked authenticated flow.

For rich results, show only enabled categories that actually have content. Unavailable tabs are hidden or labelled unavailable, never filled with generated fake search results. Always provide a way to return to the spoken answer. Enabling Images or Videos is not consent to perform a web search or load a third-party resource.

## 4 Spoken response fallback

When there is no approved rich result, display Eilo's spoken answer by default as readable text in a rounded card over the ripple. Begin only with clauses released by the native output-policy boundary to speech. Do not display speculative draft tokens, hidden reasoning or late text from cancelled turns. Text is progressive and labelled as Eilo's response; TTS callbacks determine available playback progress, without claiming proof that the user heard it. On interruption, retain only the permitted produced/spoken portion while the current session is authorized, indicate interruption and replace it with the new turn when ready.

A foreground-only working user transcript may be added only through a separately reviewed design; the default Home card contains the assistant response. Live text is not a new durable chat history. Existing explicit history consent determines what may enter the encrypted local store. Voice only suppresses the text card. When text is disabled and no enabled rich content exists, retain the wave/state with audio alone.

## 5 Rich result card

The card has a brief heading, source attribution, bounded answer or media preview, available-type tabs, close control and Keep visible. Show at most three result items initially with an explicit expand/scroll action. Separate assistant wording from source snippets. Show publication/retrieval times only when supported by real metadata. Ratings, distances, travel times and opening times are absent unless an approved provider supplies them with provenance; the user's sketch is layout guidance, not evidence of real locations or ratings. No GPS or location history is introduced. A user may explicitly include a city/place in a confirmed search query, with disclosure that it leaves the device.

Do not autoplay videos. Tap loads/plays permitted media; indicate loading and source. Pause Eilo speech and listening while video audio plays to avoid echo and self-triggering; expose Resume conversation afterwards instead of silently restarting. Browser or source-link navigation requires a user tap and a privacy notice where relevant. Links open by platform mechanisms; no general app-control feature is implied.

## 6 Lifetime and inactivity

Default card expiry is 20 seconds, separately adjustable to 10/20/60 seconds or Keep visible while unlocked. Start the timer only when speech, processing/loading and video have finished and interaction is idle. Touch, scroll, selection, accessibility focus and meaningful result interaction reset it. Respect screen-reader reading and explicit pinning rather than removing content during access. Video playback suspends expiry. Hidden visual rendering does not suspend an otherwise eligible expiry indefinitely.

Keep visible pins the current card in the current unlocked session. It is not Save to history, and cannot bypass lock, Stop, account/privacy transitions or a new request that replaces the card. Show a discreet countdown in the final few seconds, not a distracting always-running timer. Close dismisses immediately and does not stop audio/listening. Stop stops capture and clears temporary visible content. A dismissed card never reopens from an old asynchronous result. Allow “show that again” only within the still-authorized current session buffer; no recovery after Stop/lock or disabled retention.

The visual timer is independent of the existing 60-second conversation-to-standby timer. Card expiry returns to the quiet wave/state surface and does not create unsolicited speech or stop enabled wake standby.

## 7 App visibility and operating systems

| Situation | Presentation | Conditions |
|---|---|---|
| Eilo foreground and unlocked | Current spoken-response or allowed rich card | Actual native state; selected display types |
| Android outside Eilo and unlocked | Compact bounded overlay, if supported | Separate explicit overlay consent, OS special permission and viable service lifecycle |
| Android permission denied or host blocks overlay | Generic notification or voice-only fallback | No forced app launch or repeated permission prompts |
| iOS outside Eilo | Generic system notification; eligible Live Activity only after feasibility review | No arbitrary third-party Siri-style panel; system controls presentation/timing |
| Screen locked | Generic operational status only | No query, personal reply, history, thumbnail or video preview |
| App force-stopped or terminated | No availability promise | OS notices do not restart the voice engine automatically |

On Android, the overlay occupies a small part of the display, can be closed and moved away from controls, and never impersonates a system dialog or captures unrelated app input. It is off by default and respects apps that suppress overlays. Overlay permission does not grant microphone or background-listening consent. Assess permission policy and OEM behavior before release.

On iOS, notifications are a fallback and may be unavailable, suppressed or retained by the system. Use a generic “Your results are ready. Open Eilo to view them” payload, never an assistant-response snippet containing personal information. Viewing full text/images/video may require explicit opening of Eilo. Do not promise 20-second notification dismissal, arbitrary placement, automatic launch or Siri privilege. Live Activities are not unrestricted interactive web/media overlays; define eligible use before adopting them.

## 8 Search and data security

Live search is new optional scope. Core conversation, recognition, memory and TTS remain local and free. Search starts disabled. Before each outbound query, show/read a minimized query and selected provider, then receive explicit confirmation. Never transmit an entire conversation, retrieved memory, account ID, emotion profile, raw audio, exact GPS position or personal model. Allow cancellation without network traffic. Query minimization is reviewed, not assumed error-free; the user can correct a query.

Use an isolated search gateway only to protect provider credentials and enforce payload/cost limits. It must not write requests/results into Neon, application logs, caches, analytics or tracing bodies. Process query/results in bounded memory and release after delivery/cancellation. Rate protection uses narrowly retained, documented metadata only; provider IP/network access and provider retention must be disclosed. “No conversation history on our DB” remains true; “nothing ever leaves the device” is no longer accurate when the user confirms a search.

A third-party search or media service may process and retain the explicit query and network metadata. Provider contracts, regions, retention, license/attribution and billing must be assessed before live integration. If acceptable handling cannot be demonstrated, keep search disabled. No scraping, invisible trackers, arbitrary web embeds, executable HTML or unrestricted URL fetching is assumed authorized. Sanitize result text as untrusted input, validate redirects/origins/content limits and prevent server-side request forgery. Retrieved instructions never become app permissions or tool commands.

Search/media responses are session-only and caches must clear on expiry, dismissal, Stop, lock, logout or cancellation; avoid disk caches in native media libraries. With history enabled, only authorized response text can be retained under existing policy; full query/result metadata, media and URLs are not persisted as a new searchable history. Private mode persists nothing. Exact media pipeline behavior needs native cache/network inspection.

## 9 Failure states

Search offline, declined or unavailable: “I can answer from what is on your phone, but I cannot check live results right now.” Do not label local model knowledge as a search result. Media disabled: show enabled text/voice with an explanation and one deliberate enable action. Timeout: preserve the local answer; retry only by explicit action. Budget limit: explain online search availability without blocking or rationing offline conversation. Missing or unsupported overlay: use the platform fallback. Lock: clear personal content before rendering generic status. Permission revocation: remove affected surfaces and show accurate stopped/limited state.

## 10 Acceptance and traceability

Requirements VR01-VR10 cover the foreground design, SR01-SR06 cover search and OR01-OR06 cover outside-app surfaces. Each maps to one primary task in JSONv1.5; all 26 new tasks including DevOps have focused tests. Native tests must include privacy epoch races, interrupt cancellation, pin/lock, private sessions, notification payloads, media audio routes, permissions and physical-device accessibility/performance.

The generated image is a visual concept, not pixel-exact implementation evidence. The one-second GIF is a motion reference only. The old prototype 1.2 and teal contrast report are historical snapshots and do not validate this revised design. Implementation uses this specification and revised semantic tokens. No new participant, native-device, provider or App Store approval is recorded by this design merge.
