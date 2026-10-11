#include "eilo_asr.h"
#include "moonshine-c-api.h"
#include <cmath>
#include <cstring>
#include <memory>

struct EiloAsr {
  int32_t transcriber=-1,stream=-1;int64_t samples=0;bool finished=false,failed=false;
  ~EiloAsr(){if(stream>=0)moonshine_free_stream(transcriber,stream);if(transcriber>=0)moonshine_free_transcriber(transcriber);}
};
extern "C" EiloAsr *eilo_asr_create(const char *directory) {
  try {
    if(!directory || directory[0]!='/' || strnlen(directory,4097)>4096 || moonshine_get_version()!=MOONSHINE_HEADER_VERSION)return nullptr;
    auto a=std::make_unique<EiloAsr>();
    const moonshine_option_t options[]={{"log_ort_run","false"},{"identify_speakers","false"},{"word_timestamps","false"}};
    a->transcriber=moonshine_load_transcriber_from_files(directory,MOONSHINE_MODEL_ARCH_SMALL_STREAMING,options,3,MOONSHINE_HEADER_VERSION);
    if(a->transcriber<0)return nullptr;
    a->stream=moonshine_create_stream(a->transcriber,0);
    if(a->stream<0 || moonshine_start_stream(a->transcriber,a->stream)!=0)return nullptr;
    return a.release();
  }catch(...){return nullptr;}
}
extern "C" int32_t eilo_asr_accept(EiloAsr *a,const float *pcm,int32_t count) {
  if(!a || a->finished || a->failed)return -1;
  try {
    if(!pcm || count<1 || count>1600 || a->samples>480000-count){a->failed=true;return -1;}
    for(int i=0;i<count;++i)if(!std::isfinite(pcm[i]) || pcm[i]<-1 || pcm[i]>1){a->failed=true;return -1;}
    if(moonshine_transcribe_add_audio_to_stream(a->transcriber,a->stream,pcm,count,16000,0)!=0){a->failed=true;return -1;}
    a->samples+=count;return 0;
  }catch(...){a->failed=true;return -1;}
}
extern "C" int32_t eilo_asr_text(EiloAsr *a,int32_t finish,char *out,int32_t capacity) {
  if(out && capacity==4097)std::memset(out,0,4097);
  if(!a || a->failed || a->finished || !out || capacity!=4097 || (finish!=0 && finish!=1))return -1;
  try {
    if(finish && moonshine_stop_stream(a->transcriber,a->stream)!=0){a->failed=true;return -1;}
    transcript_t *transcript=nullptr;
    if(moonshine_transcribe_stream(a->transcriber,a->stream,0,&transcript)!=0 || !transcript || transcript->line_count>64 || (transcript->line_count && !transcript->lines)){a->failed=true;return -1;}
    size_t size=0;
    for(uint64_t i=0;i<transcript->line_count;++i){
      const auto &line=transcript->lines[i];if(!line.text || (finish && !line.is_complete)){a->failed=true;break;}
      size_t n=strnlen(line.text,4097);if(n>4096 || size+n+(size && n?1:0)>4096){a->failed=true;break;}
      if(!n)continue;
      for(size_t k=0;k<n;++k){unsigned char c=static_cast<unsigned char>(line.text[k]);if(c<32 && c!=9 && c!=10){a->failed=true;break;}}
      if(a->failed)break;
      if(size)out[size++]=' ';
      std::memcpy(out+size,line.text,n);size+=n;
    }
    if(a->failed){std::memset(out,0,4097);return -1;}
    out[size]=0;a->finished=finish!=0;return 0;
  }catch(...){std::memset(out,0,4097);a->failed=true;return -1;}
}
extern "C" void eilo_asr_destroy(EiloAsr *a){try{delete a;}catch(...){}}
