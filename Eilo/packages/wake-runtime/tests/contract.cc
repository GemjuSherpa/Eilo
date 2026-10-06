// Scripted C ABI contract checks; these do not measure acoustic recognition.
#include "eilo_wake.h"
#include "sherpa-onnx/c-api/c-api.h"
#include <cassert>
#include <cmath>
#include <cstring>
#include <stdexcept>

struct SherpaOnnxKeywordSpotter {};
struct SherpaOnnxOnlineStream {};
static SherpaOnnxKeywordSpotter spotter;
static SherpaOnnxOnlineStream stream;
static int decoded, accepted, resets, results, freed_results, freed_streams, freed_models;
static bool endless, fail_result, fail_stream, throw_decode;
static const char *keyword = "HEY_EILO";
extern "C" {
const SherpaOnnxKeywordSpotter *SherpaOnnxCreateKeywordSpotter(const SherpaOnnxKeywordSpotterConfig *c) {
  assert(c->feat_config.sample_rate == 16000 && c->model_config.num_threads == 1);
  assert(std::strstr(c->keywords_buf, "@HEY_EILO\n"));
  return &spotter;
}
const SherpaOnnxOnlineStream *SherpaOnnxCreateKeywordStream(const SherpaOnnxKeywordSpotter *) { return fail_stream ? nullptr : &stream; }
void SherpaOnnxDestroyKeywordSpotter(const SherpaOnnxKeywordSpotter *) { ++freed_models; }
void SherpaOnnxDestroyOnlineStream(const SherpaOnnxOnlineStream *) { ++freed_streams; }
void SherpaOnnxOnlineStreamAcceptWaveform(const SherpaOnnxOnlineStream *, int32_t, const float *, int32_t) { ++accepted; }
int32_t SherpaOnnxIsKeywordStreamReady(const SherpaOnnxKeywordSpotter *, const SherpaOnnxOnlineStream *) { return endless || decoded < 2; }
void SherpaOnnxDecodeKeywordStream(const SherpaOnnxKeywordSpotter *, const SherpaOnnxOnlineStream *) {
  ++decoded;
  if (throw_decode) throw std::runtime_error("synthetic");
}
const SherpaOnnxKeywordResult *SherpaOnnxGetKeywordResult(const SherpaOnnxKeywordSpotter *, const SherpaOnnxOnlineStream *) {
  ++results;
  if (fail_result) return nullptr;
  auto *r = new SherpaOnnxKeywordResult{};
  r->keyword = decoded == 1 ? keyword : "";
  return r;
}
void SherpaOnnxDestroyKeywordResult(const SherpaOnnxKeywordResult *r) { ++freed_results; delete r; }
void SherpaOnnxResetKeywordStream(const SherpaOnnxKeywordSpotter *, const SherpaOnnxOnlineStream *) { ++resets; }
}
static EiloWake *open() {
  decoded=accepted=resets=results=freed_results=freed_streams=freed_models=0;
  return eilo_wake_create("encoder", "decoder", "joiner", "tokens", 0.25f, 1.5f);
}
int main() {
  float samples[320]{};
  // A trigger in decode one must survive a later empty result in the same frame.
  auto *w=open(); assert(w); assert(eilo_wake_process(w,samples,320,16000)==1);
  assert(decoded==2 && results==2 && freed_results==2 && resets==1);
  assert(eilo_wake_process(w,samples,320,16000)==0); eilo_wake_destroy(w);
  assert(freed_streams==1 && freed_models==1);
  keyword="OTHER";w=open();assert(eilo_wake_process(w,samples,320,16000)==0);assert(resets==1);eilo_wake_destroy(w);keyword="HEY_EILO";
  fail_stream=true;w=open();assert(!w && freed_models==1 && freed_streams==0);fail_stream=false;
  for(int scenario=0;scenario<8;++scenario) {
    w=open();assert(w);
    int count=320,rate=16000;const float *input=samples;
    if(scenario==0) input=nullptr;
    if(scenario==1) count=0;
    if(scenario==2) count=1601;
    if(scenario==3) rate=7999;
    if(scenario==4) samples[0]=NAN;
    if(scenario==5) samples[0]=1.1f;
    if(scenario==6) fail_result=true;
    if(scenario==7) throw_decode=true;
    assert(eilo_wake_process(w,input,count,rate)==-1);
    samples[0]=0;fail_result=throw_decode=false;
    assert(eilo_wake_process(w,samples,320,16000)==-1);eilo_wake_destroy(w);
    assert(freed_streams==1 && freed_models==1);
  }
  endless=true;w=open();assert(eilo_wake_process(w,samples,320,16000)==-1);assert(decoded==32);eilo_wake_destroy(w);endless=false;
  w=open();assert(eilo_wake_process(w,samples,320,16000)==1);assert(eilo_wake_process(w,samples,320,48000)==-1);eilo_wake_destroy(w);
  assert(!eilo_wake_create(nullptr,"d","j","t",0.25f,1.5f));
  assert(!eilo_wake_create("e","d","j","t",NAN,1.5f));
  assert(!eilo_wake_create("e","d","j","t",0.25f,11));
  assert(eilo_wake_process(nullptr,samples,320,16000)==-1);eilo_wake_destroy(nullptr);
}
