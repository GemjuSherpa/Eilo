// Appended to the existing scripted backend prefix by check_resident_contract.py.
#include "eilo_trial_residency.h"
#include "eilo_trial_metrics.h"
#include <thread>
static void run_generation(int fd,int iteration,int candidate) {
  current=eilo_llm_create(); CHECK(current);
  CHECK(eilo_llm_create()==nullptr); // One live scoped handle.
  begun(fd); CHECK(eilo_trial_residency_end()==0);
  CHECK(next()==1); CHECK(next()==1); CHECK(next()==0);
  eilo_llm_destroy(current); current=nullptr; CHECK(live==1); // Only the generic model survives, not context/sampler/batch.
  int32_t stats[5]{}; CHECK(eilo_trial_residency_stats(stats,5)==1);
  CHECK(stats[0]==1 && stats[1]==iteration && stats[2]==1 && stats[3]==0 && stats[4]==candidate);
  double metrics[7]{}; CHECK(eilo_trial_phase_metrics(metrics,7)==1);
  if(iteration>1)CHECK(metrics[0]==0);
}
int main() {
  reset(); finish();
  CHECK(eilo_trial_residency_begin(-1)==0 && eilo_trial_residency_begin(2)==0);
  FILE *file=std::tmpfile(); CHECK(file); int fd=fileno(file); CHECK(ftruncate(fd,1282439424)==0);
  CHECK(eilo_trial_residency_begin(0)==1 && eilo_trial_residency_begin(0)==0);
  for(int i=1;i<=3;++i)run_generation(fd,i,0);
  CHECK(resident_load_calls==1 && resident_context_calls==3 && resident_kv_clears==3);
  current=eilo_llm_create();CHECK(current);CHECK(eilo_llm_load(current,fd,2)==-1);finish();CHECK(live==0); // Fourth load revokes scope.
  int32_t stats[5]={99,99,99,99,99};CHECK(eilo_trial_residency_stats(stats,5)==0);for(auto v:stats)CHECK(v==0);
  CHECK(eilo_trial_residency_begin(0)==1);run_generation(fd,1,0);
  std::thread other([]{int32_t s[5]{};CHECK(eilo_trial_residency_stats(s,5)==0);CHECK(eilo_trial_residency_end()==1);});other.join();CHECK(live==1);
  current=eilo_llm_create();CHECK(current);loaded(fd);CHECK(eilo_llm_begin(current,"fixture",7,2)==0);
  eilo_llm_cancel(current);CHECK(next()==-2);finish();CHECK(live==0);CHECK(eilo_trial_residency_stats(stats,5)==0);
  CHECK(eilo_trial_residency_begin(0)==1);run_generation(fd,1,0);
  current=eilo_llm_create();CHECK(current);loaded(fd);finish();CHECK(live==0); // Abandoned generation revokes cache.
  CHECK(eilo_trial_residency_begin(0)==1);run_generation(fd,1,0);
  FILE *other_file=std::tmpfile();CHECK(other_file);CHECK(ftruncate(fileno(other_file),1282439424)==0);
  current=eilo_llm_create();CHECK(current);CHECK(eilo_llm_load(current,fileno(other_file),2)==-1);finish();CHECK(live==0); // Different verified inode cannot reuse weights.
  CHECK(eilo_trial_residency_begin(0)==1);run_generation(fd,1,0);
  current=eilo_llm_create();CHECK(current);CHECK(eilo_llm_load(current,fd,3)==-1);finish();CHECK(live==0);
  CHECK(ftruncate(fd,484219808)==0);CHECK(eilo_trial_residency_begin(1)==1);
  for(int i=1;i<=3;++i)run_generation(fd,i,1);
  stats[0]=123;CHECK(eilo_trial_residency_stats(stats,4)==0 && stats[0]==123);
  CHECK(eilo_trial_residency_stats(nullptr,5)==0);
  CHECK(eilo_trial_residency_end()==1 && live==0 && eilo_trial_residency_end()==1);
  double metrics[7]{};CHECK(eilo_trial_phase_metrics(metrics,7)==0);
  std::fclose(other_file);std::fclose(file);
  std::puts("Resident lab contracts: one model, three fresh contexts/KV clears, both sizes, scope/cancel/failure/abandonment/inode/thread revocation PASS");
  return 0;
}
