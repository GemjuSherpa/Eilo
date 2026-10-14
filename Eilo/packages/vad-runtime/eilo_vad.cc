#include "eilo_vad.h"
#include "vad_backend.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <memory>

namespace {
void erase(float *p, size_t count) {volatile float *v=p;while(count--)*v++=0;}
}
struct EiloVad {
  std::unique_ptr<VadBackend> backend;
  std::array<float,256> state{};
  std::array<float,64> context{};
  int32_t samples=0;
  bool terminal=false;
  void clear(){erase(state.data(),state.size());erase(context.data(),context.size());}
  ~EiloVad(){clear();}
};
extern "C" EiloVad *eilo_vad_create(const char *model) {
  try {
    if(!model || model[0]!='/' || strnlen(model,4097)>4096)return nullptr;
    auto stream=std::make_unique<EiloVad>();
    stream->backend=open_vad_backend(model);
    return stream->backend?stream.release():nullptr;
  }catch(...){return nullptr;}
}
extern "C" int32_t eilo_vad_process(EiloVad *stream,const float *pcm,int32_t count,
                                    int32_t final_frame,EiloVadFrame *out) {
  if(out)*out={-1,0,0,0};
  if(!stream)return -1;
  auto fail=[&](){stream->terminal=true;stream->clear();return -1;};
  if(stream->terminal || !pcm || !out || count<1 || count>512 ||
     (final_frame!=0 && final_frame!=1) || (!final_frame && count!=512) ||
     stream->samples>480000-count)return fail();
  for(int32_t i=0;i<count;++i)if(!std::isfinite(pcm[i]) || pcm[i]<-1 || pcm[i]>1)return fail();
  std::array<float,576> input{};
  std::array<float,256> next{};
  struct Scratch {
    std::array<float,576> &input;std::array<float,256> &next;
    ~Scratch(){erase(input.data(),input.size());erase(next.data(),next.size());}
  } scratch{input,next};
  try {
    std::copy(stream->context.begin(),stream->context.end(),input.begin());
    std::copy(pcm,pcm+count,input.begin()+64);
    float probability=-1;
    if(!stream->backend->infer(input.data(),stream->state.data(),&probability,next.data()) ||
       !std::isfinite(probability) || probability<0 || probability>1)return fail();
    for(float value:next)if(!std::isfinite(value))return fail();
    stream->state=next;
    std::copy(input.end()-64,input.end(),stream->context.begin());
    *out={probability,stream->samples,count,final_frame};
    stream->samples+=count;
    if(final_frame){stream->terminal=true;stream->clear();}
    return 0;
  }catch(...){return fail();}
}
extern "C" void eilo_vad_destroy(EiloVad *stream){try{delete stream;}catch(...){}}
