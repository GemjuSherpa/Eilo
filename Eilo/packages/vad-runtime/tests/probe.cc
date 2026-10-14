#include "eilo_vad.h"
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
int main(int argc,char **argv){
  if(argc!=2)return 2;
  std::array<float,512> pcm{};std::array<float,32> reference{};
  float maximum=0;
  for(int repeat=0;repeat<2;++repeat){
    auto *stream=eilo_vad_create(argv[1]);if(!stream)return 3;
    for(int i=0;i<32;++i){
      EiloVadFrame out{};const int count=i==31?129:512;
      if(eilo_vad_process(stream,pcm.data(),count,i==31,&out)!=0 ||
         out.start_sample!=i*512 || out.samples!=count || out.final_frame!=(i==31) ||
         !std::isfinite(out.probability) || out.probability<0 || out.probability>1){eilo_vad_destroy(stream);return 4;}
      if(repeat==0)reference[i]=out.probability;
      else maximum=std::max(maximum,std::abs(out.probability-reference[i]));
    }
    EiloVadFrame rejected{};
    if(eilo_vad_process(stream,pcm.data(),512,0,&rejected)!=-1 || rejected.probability!=-1){eilo_vad_destroy(stream);return 5;}
    eilo_vad_destroy(stream);
  }
  if(maximum>0.000001f)return 6;
  std::cout<<std::setprecision(10)<<"{\"status\":\"EXECUTED_SYNTHETIC\",\"windows_per_stream\":32,\"valid_samples\":16001,\"first_probability\":"<<reference[0]
    <<",\"repeat_max_abs_delta\":"<<maximum<<",\"post_final_rejected\":true}"<<std::endl;
}
