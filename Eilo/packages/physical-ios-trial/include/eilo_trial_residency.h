#ifndef EILO_TRIAL_RESIDENCY_H
#define EILO_TRIAL_RESIDENCY_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Lab only. Worker-owned scope; 0=exact pinned 1.7B, 1=exact pinned 0.6B.
 * Caller must hash each immutable signed-store descriptor with the selected pin.
 * At most one live handle/model, three generations; every generation clears KV,
 * context, sampler and batch. Only generic weights survive successful DONE.
 * Scope close/failure/revocation frees weights. End only after joining/destroying
 * the worker's handle. No process-global cache or ordinary app activation. */
int32_t eilo_trial_residency_begin(int32_t candidate);
int32_t eilo_trial_residency_end(void);
/* Same worker after completed handle destruction. Exactly five integers:
 * vendor model loads, generation loads, resident models, live handles, candidate.
 * Wrong capacity writes nothing; unavailable valid-capacity read clears outputs. */
int32_t eilo_trial_residency_stats(int32_t *output, int32_t count);
#ifdef __cplusplus
}
#endif
#endif
