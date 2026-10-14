#include "eilo_vad.h"
#include "vad_backend.h"
#include <array>
#include <cassert>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace {
int mode=0,calls=0,closed=0,opened=0;
class Fake final:public VadBackend {
public:
  ~Fake() override {++closed;}
  bool infer(const float *input,const float *state,float *probability,float *next) override {
    ++calls;
    if(mode==1)return false;
    if(mode==2)throw std::runtime_error("scripted failure");
    if(mode==3){*probability=std::numeric_limits<float>::quiet_NaN();return true;}
    if(mode==4){*probability=1.1f;return true;}
    if(mode==5){*probability=.9f;next[0]=std::numeric_limits<float>::infinity();return true;}
    if(mode==6){for(int i=0;i<64;++i)assert(input[i]==.25f);assert(state[0]==1);}
    if(mode==7){for(int i=0;i<64;++i)assert(input[i]==0);assert(state[0]==0);}
    if(mode==8){for(int i=64+7;i<576;++i)assert(input[i]==0);}
    *probability=.9f;next[0]=state[0]+1;return true;
  }
};
}
std::unique_ptr<VadBackend> open_vad_backend(const char *model){
  if(std::strcmp(model,"/throw")==0)throw std::runtime_error("open");
  if(std::strcmp(model,"/null")==0)return nullptr;
  ++opened;return std::make_unique<Fake>();
}
int main(){
  std::array<float,512> pcm{};pcm.fill(.25f);EiloVadFrame frame{};
  assert(!eilo_vad_create(nullptr));assert(!eilo_vad_create("relative"));
  assert(!eilo_vad_create("/throw"));assert(!eilo_vad_create("/null"));
  assert(eilo_vad_process(nullptr,pcm.data(),512,0,&frame)==-1);assert(frame.probability==-1);
  auto stream=eilo_vad_create("/model");assert(stream);
  mode=7;assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==0);
  assert(frame.start_sample==0 && frame.samples==512 && frame.probability==.9f);
  mode=6;assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==0);assert(frame.start_sample==512);
  mode=8;assert(eilo_vad_process(stream,pcm.data(),7,1,&frame)==0);
  assert(frame.start_sample==1024 && frame.samples==7 && frame.final_frame==1);
  const int before=calls;
  assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==-1);assert(calls==before);
  eilo_vad_destroy(stream);
  for(int fail=1;fail<=5;++fail){
    stream=eilo_vad_create("/model");mode=fail;
    assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==-1);assert(frame.probability==-1);
    mode=0;const int stopped=calls;
    assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==-1);assert(calls==stopped);
    eilo_vad_destroy(stream);
  }
  for(int bad=0;bad<7;++bad){
    stream=eilo_vad_create("/model");int count=512,final=0;const float *input=pcm.data();auto *out=&frame;
    if(bad==0)count=0;if(bad==1)count=513;if(bad==2)count=7;
    if(bad==3)final=2;if(bad==4)input=nullptr;if(bad==5)out=nullptr;
    if(bad==6)pcm[0]=std::numeric_limits<float>::quiet_NaN();
    const int stopped=calls;
    assert(eilo_vad_process(stream,input,count,final,out)==-1);assert(calls==stopped);
    pcm[0]=.25f;assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==-1);
    eilo_vad_destroy(stream);
  }
  for(float invalid:{-1.01f,1.01f,std::numeric_limits<float>::infinity()}){
    stream=eilo_vad_create("/model");pcm[0]=invalid;
    assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==-1);eilo_vad_destroy(stream);
  }
  pcm[0]=.25f;stream=eilo_vad_create("/model");mode=0;
  for(int i=0;i<937;++i)assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==0);
  assert(eilo_vad_process(stream,pcm.data(),256,1,&frame)==0);assert(frame.start_sample+frame.samples==480000);
  eilo_vad_destroy(stream);
  stream=eilo_vad_create("/model");
  for(int i=0;i<937;++i)assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==0);
  assert(eilo_vad_process(stream,pcm.data(),512,0,&frame)==-1);eilo_vad_destroy(stream);
  mode=7;stream=eilo_vad_create("/model");assert(eilo_vad_process(stream,pcm.data(),512,1,&frame)==0);
  eilo_vad_destroy(stream);eilo_vad_destroy(nullptr);assert(closed==opened);
}
