#include "eilo_wake.h"
#include "sherpa-onnx/c-api/c-api.h"
#include <cmath>
#include <cstring>
#include <new>

struct EiloWake {
  const SherpaOnnxKeywordSpotter *spotter = nullptr;
  const SherpaOnnxOnlineStream *stream = nullptr;
  bool failed = false;
  int32_t sample_rate = 0;
};
extern "C" void eilo_wake_destroy(EiloWake *w) {
  if (!w) return;
  if (w->stream) SherpaOnnxDestroyOnlineStream(w->stream);
  if (w->spotter) SherpaOnnxDestroyKeywordSpotter(w->spotter);
  delete w;
}
extern "C" EiloWake *eilo_wake_create(const char *encoder, const char *decoder,
                                      const char *joiner, const char *tokens,
                                      float threshold, float boost) {
  if (!encoder || !decoder || !joiner || !tokens || !*encoder || !*decoder || !*joiner || !*tokens ||
      !std::isfinite(threshold) || threshold <= 0 || threshold > 1 ||
      !std::isfinite(boost) || boost <= 0 || boost > 10) return nullptr;
  auto *w = new (std::nothrow) EiloWake;
  if (!w) return nullptr;
  try {
    SherpaOnnxKeywordSpotterConfig c{};
    c.feat_config.sample_rate = 16000; c.feat_config.feature_dim = 80;
    c.model_config.transducer.encoder = encoder;
    c.model_config.transducer.decoder = decoder;
    c.model_config.transducer.joiner = joiner;
    c.model_config.tokens = tokens; c.model_config.num_threads = 1;
    c.model_config.provider = "cpu"; c.model_config.debug = 0;
    c.max_active_paths = 4; c.num_trailing_blanks = 1;
    c.keywords_threshold = threshold; c.keywords_score = boost;
    // Candidate phonetic spelling HEY ALO for Gemju Sherpa's Ay-loh selection.
    // This spelling is under evaluation, not a calibrated production lexicon.
    const char keyword[] = "\xE2\x96\x81HE Y \xE2\x96\x81" "A LO @HEY_EILO\n";
    c.keywords_buf = keyword; c.keywords_buf_size = static_cast<int32_t>(sizeof(keyword)-1);
    w->spotter = SherpaOnnxCreateKeywordSpotter(&c);
    if (w->spotter) w->stream = SherpaOnnxCreateKeywordStream(w->spotter);
    if (!w->stream) { eilo_wake_destroy(w); return nullptr; }
    return w;
  } catch (...) { eilo_wake_destroy(w); return nullptr; }
}
extern "C" int32_t eilo_wake_process(EiloWake *w, const float *samples, int32_t count, int32_t rate) {
  if (!w || w->failed) return -1;
  if (!samples || rate < 8000 || rate > 192000 || count <= 0 || count > rate/10) { w->failed = true; return -1; }
  if (w->sample_rate != 0 && w->sample_rate != rate) { w->failed = true; return -1; }
  w->sample_rate = rate;
  for (int32_t i=0;i<count;++i) if (!std::isfinite(samples[i]) || samples[i]<-1 || samples[i]>1) { w->failed=true;return -1; }
  const SherpaOnnxKeywordResult *result = nullptr;
  try {
    SherpaOnnxOnlineStreamAcceptWaveform(w->stream,rate,samples,count);
    int steps=0;
    bool matched=false;
    while (SherpaOnnxIsKeywordStreamReady(w->spotter,w->stream)) {
      if (++steps>32) { w->failed=true;return -1; }
      SherpaOnnxDecodeKeywordStream(w->spotter,w->stream);
      result=SherpaOnnxGetKeywordResult(w->spotter,w->stream);
      if (!result || !result->keyword) {
        w->failed=true;
        if(result) SherpaOnnxDestroyKeywordResult(result);
        return -1;
      }
      matched=matched || std::strcmp(result->keyword,"HEY_EILO")==0;
      const bool nonempty=*result->keyword != '\0';
      SherpaOnnxDestroyKeywordResult(result);result=nullptr;
      if (nonempty) SherpaOnnxResetKeywordStream(w->spotter,w->stream);
    }
    return matched ? 1 : 0;
  } catch (...) {
    if(result)SherpaOnnxDestroyKeywordResult(result);
    w->failed=true;return -1;
  }
}
