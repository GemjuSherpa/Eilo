// Synthetic fixture runner only. No microphone, application diagnostics or production logging.
#include "eilo_asr.h"
#include <array>
#include <fstream>
#include <iostream>
#include <memory>
#include <vector>
int main(int argc,char **argv){
  if(argc!=3)return 2;
  std::ifstream f(argv[2],std::ios::binary|std::ios::ate);
  if(!f || f.tellg()<=0 || f.tellg()>480000*4 || f.tellg()%4!=0)return 2;
  const size_t n=static_cast<size_t>(f.tellg())/4;std::vector<float> pcm(n);f.seekg(0);f.read(reinterpret_cast<char *>(pcm.data()),n*4);
  std::unique_ptr<EiloAsr,decltype(&eilo_asr_destroy)> a(eilo_asr_create(argv[1]),eilo_asr_destroy);
  if(!a)return 2;
  std::array<char,4097> text{};size_t frames=0;
  for(size_t i=0;i<n;i+=320){
    size_t count=std::min(static_cast<size_t>(320),n-i);
    if(eilo_asr_accept(a.get(),pcm.data()+i,static_cast<int32_t>(count))!=0)return 2;
    if(++frames%10==0 && eilo_asr_text(a.get(),0,text.data(),4097)!=0)return 2;
    text.fill(0);
  }
  std::fill(pcm.begin(),pcm.end(),0);
  if(eilo_asr_text(a.get(),1,text.data(),4097)!=0)return 2;
  std::cout<<text.data()<<std::endl;text.fill(0);
  // Closed/finalized streams cannot accept or produce a second final.
  float sample=0;
  if(eilo_asr_accept(a.get(),&sample,1)!=-1 || eilo_asr_text(a.get(),1,text.data(),4097)!=-1)return 3;
  for(char value:text)if(value)return 3;
  return 0;
}
