"""Opt-in one-model lab residency scopes, derived from exact reviewed phase source."""
import hashlib
from model_wrapper import PINS
from phase_wrapper import phase_wrapper

CANDIDATES = (
    ('Qwen3-1.7B-Q4_K_M',1282439424,'c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120'),
    ('Qwen3-0.6B-Q4_K_M',484219808,'9b1a69f90cc7b7404ffeabd12f58391a6323ea08ae6e517f6cfd56bbb2caf5ca'),
)


def resident_wrapper(source):
    if any(PINS.get(m)!=(size,digest) for m,size,digest in CANDIDATES):raise ValueError('Unreviewed residency candidate inventory')
    model,size,digest=CANDIDATES[0]
    compiled,evidence=phase_wrapper(source,dict(model=model,bytes=size,sha256=digest))
    phase_digest=hashlib.sha256(compiled).hexdigest()
    def change(old,new):
        nonlocal compiled
        old,new=old.encode(),new.encode()
        if compiled.count(old)!=1:raise ValueError('Unreviewed residency insertion boundary')
        compiled=compiled.replace(old,new)
    change('#include "eilo_trial_metrics.h"','#include "eilo_trial_metrics.h"\n#include "eilo_trial_residency.h"')
    change('constexpr int64_t kModelBytes = 1282439424;', '''constexpr int64_t kModelBytes = 1282439424;
struct TrialResidency {
  llama_model *model = nullptr;
  bool active = false;
  int candidate = -1, live = 0, model_loads = 0, generations = 0, threads = 0;
  dev_t device{}; ino_t inode{};
  int64_t required_bytes() const { return active && candidate == 1 ? 484219808 : kModelBytes; }
  void drop() {
    if (model) { llama_model_free(model); model = nullptr; }
    active = false; candidate = -1; model_loads = generations = threads = 0;
    device = {}; inode = {};
  }
  ~TrialResidency() { drop(); }
};
thread_local TrialResidency trial_residency;''')
    change('  void clear() {','  EiloLlm() { ++trial_residency.live; }\n  void clear() {')
    change('if (model) { llama_model_free(model); model = nullptr; }\n  }\n  ~EiloLlm() { clear(); }', '''if (model) {
      if (model != trial_residency.model) llama_model_free(model);
      model = nullptr;
    }
  }
  ~EiloLlm() {
    clear();
    if (state != State::done) trial_residency.drop();
    --trial_residency.live;
  }''')
    change('clear(); state = reason == EILO_LLM_DONE ? State::done : State::failed;', '''clear();
    if (reason != EILO_LLM_DONE) trial_residency.drop();
    state = reason == EILO_LLM_DONE ? State::done : State::failed;''')
    change('  try { return new EiloLlm; }', '''  if (trial_residency.active && trial_residency.live != 0) return nullptr;
  try { return new EiloLlm; }''')
    change('info.st_size != kModelBytes','info.st_size != trial_residency.required_bytes()')
    change('    int copy = dup(fd);', '''    if (trial_residency.active && (trial_residency.generations >= 3 ||
        (trial_residency.model && (info.st_dev != trial_residency.device || info.st_ino != trial_residency.inode || threads != trial_residency.threads))))
      return h->stop(EILO_LLM_INVALID);
    int copy = dup(fd);''')
    change('''h->model = llama_model_load_from_file_ptr(file, params);
    trial_metrics.values[0] = trial_ms(trial_load_start);''','''if (trial_residency.active && trial_residency.model) {
      h->model = trial_residency.model;
      trial_metrics.values[0] = 0; // No vendor load call on a warm sample.
    } else {
      h->model = llama_model_load_from_file_ptr(file, params);
      trial_metrics.values[0] = trial_ms(trial_load_start);
    }''')
    change('    h->threads = threads; h->state', '''    if (trial_residency.active) {
      if (!trial_residency.model) {
        trial_residency.model = h->model; trial_residency.model_loads = 1;
        trial_residency.device = info.st_dev; trial_residency.inode = info.st_ino; trial_residency.threads = threads;
      }
      ++trial_residency.generations;
    }
    h->threads = threads; h->state''')
    compiled+=b'''
// One serialized worker owns scopes and all handles. No paths/content enter this API.
extern "C" int32_t eilo_trial_residency_begin(int32_t candidate) {
  if (candidate < 0 || candidate > 1 || trial_residency.active || trial_residency.live != 0) return 0;
  trial_residency.drop(); trial_metrics = TrialMetrics{};
  trial_residency.active = true; trial_residency.candidate = candidate;
  return 1;
}
extern "C" int32_t eilo_trial_residency_end(void) {
  if (trial_residency.live != 0) return 0;
  trial_residency.drop(); trial_metrics = TrialMetrics{};
  return 1;
}
extern "C" int32_t eilo_trial_residency_stats(int32_t *out, int32_t count) {
  if (!out || count != 5) return 0;
  for (int i = 0; i < count; ++i) out[i] = 0;
  if (!trial_residency.active || trial_residency.live != 0 || !trial_metrics.complete) return 0;
  out[0] = trial_residency.model_loads; out[1] = trial_residency.generations;
  out[2] = trial_residency.model ? 1 : 0; out[3] = trial_residency.live; out[4] = trial_residency.candidate;
  return 1;
}
'''
    evidence.update(scope='LAB_ONLY_EXACT_TWO_MODEL_RESIDENCY',phase_source_sha256=phase_digest,
                    compiled_source_sha256=hashlib.sha256(compiled).hexdigest(),
                    candidates=[dict(index=i,model=m,bytes=PINS[m][0],sha256=PINS[m][1]) for i,(m,_,_) in enumerate(CANDIDATES)],
                    change='Explicit worker-only one-generic-model scope, at most three generations; per-generation KV/context/sampler cleanup retained; scope close/failure frees cached weights; ordinary adapter unchanged')
    return compiled,evidence
