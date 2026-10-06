#include "eilo_wake.h"
#include "sherpa-onnx/c-api/c-api.h"
#include <algorithm>
#include <cstdio>
#include <string>
#include <vector>
int main(int argc,char **argv) {
  if(argc!=5)return 2;
  const std::string m=argv[1];
  auto *w=eilo_wake_create((m+"/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx").c_str(),
                         (m+"/decoder-epoch-12-avg-2-chunk-16-left-64.onnx").c_str(),
                         (m+"/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx").c_str(),
                         (m+"/tokens.txt").c_str(),std::stof(argv[3]),std::stof(argv[4]));
  if(!w)return 3;
  const auto *wave=SherpaOnnxReadWave(argv[2]);if(!wave){eilo_wake_destroy(w);return 4;}
  int detections=0;const int frame=wave->sample_rate/50;
  for(int offset=0;offset<wave->num_samples;offset+=frame){const int r=eilo_wake_process(w,wave->samples+offset,std::min(frame,wave->num_samples-offset),wave->sample_rate);if(r<0){SherpaOnnxFreeWave(wave);eilo_wake_destroy(w);return 5;}detections+=r;}
  std::vector<float> tail(frame,0);
  for(int i=0;i<50;++i){const int r=eilo_wake_process(w,tail.data(),frame,wave->sample_rate);if(r<0){SherpaOnnxFreeWave(wave);eilo_wake_destroy(w);return 6;}detections+=r;}
  SherpaOnnxFreeWave(wave);eilo_wake_destroy(w);
  std::printf("{\"detections\":%d}\n",detections);return 0;
}
