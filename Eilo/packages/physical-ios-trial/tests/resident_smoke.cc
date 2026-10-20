// Explicit fixed-input real-runtime probe; caller verifies exact SHA before launch.
#include "eilo_llm.h"
#include "eilo_trial_metrics.h"
#include "eilo_trial_residency.h"
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <cstdio>
int main(int argc,char **argv){
  if(argc!=3 || (std::strcmp(argv[2],"0") && std::strcmp(argv[2],"1")))return 2;
  const int candidate=argv[2][0]-'0';
  int fd=open(argv[1],O_RDONLY|O_NOFOLLOW);if(fd<0)return 2;
  if(eilo_trial_residency_begin(candidate)!=1){close(fd);return 3;}
  for(int iteration=1;iteration<=3;++iteration){
    auto *h=eilo_llm_create();if(!h)return 4;
    if(eilo_llm_load(h,fd,2)!=0)return 5;
    const char prompt[]="<|im_start|>user\nSay hello.\n<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
    if(eilo_llm_count_tokens(h,prompt,std::strlen(prompt))<1 || eilo_llm_begin(h,prompt,std::strlen(prompt),8)!=0)return 6;
    char out[1024]{};int32_t bytes=0;int pieces=0,status=0;
    while((status=eilo_llm_next(h,out,sizeof(out),&bytes))==1){
      if(bytes<1 || ++pieces>8)return 7;std::memset(out,0,sizeof(out));
    }
    eilo_llm_cancel(h);eilo_llm_destroy(h);std::memset(out,0,sizeof(out));
    int32_t stats[5]{};double metrics[7]{};
    if(status!=0 || pieces<1 || eilo_trial_residency_stats(stats,5)!=1 || eilo_trial_phase_metrics(metrics,7)!=1)return 8;
    if(stats[0]!=1 || stats[1]!=iteration || stats[2]!=1 || stats[3]!=0 || stats[4]!=candidate || (iteration>1 && metrics[0]!=0))return 9;
  }
  close(fd);if(eilo_trial_residency_end()!=1)return 10;
  std::puts("Pinned real CPU model: one load, three generations, warm reuse and scope cleanup PASS; no output content exported");
  return 0;
}
