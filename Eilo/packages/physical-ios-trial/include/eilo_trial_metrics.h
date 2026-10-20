#ifndef EILO_TRIAL_METRICS_H
#define EILO_TRIAL_METRICS_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Same worker thread, after successful completion/destruction, before next load.
 * Exactly seven doubles: native model load, begin tokenization, context/sampler/
 * batch setup, prompt decode (prefill), first sampling call, begin-to-first-token,
 * begin-to-first-piece-ready, all milliseconds. Numeric aggregates only.
 * Failure/cancellation and a new load revoke the prior snapshot. Wrong capacity
 * writes nothing. A valid-capacity unavailable read clears all seven outputs. */
int32_t eilo_trial_phase_metrics(double *output, int32_t count);
#ifdef __cplusplus
}
#endif
#endif
