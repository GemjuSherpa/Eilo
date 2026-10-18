import Foundation
@main struct SurveyProbe {
 static func main(){
  let s=TrialVoiceSurvey();precondition(!s.rate(5))
  let (old,f)=s.begin()!;precondition(f==1 && s.begin()==nil && !s.rate(5))
  s.cancel();precondition(!s.finish(old) && !s.rate(5))
  let (retry,_)=s.begin()!;precondition(!s.finish(old) && s.finish(retry) && !s.finish(retry))
  precondition(!s.rate(0) && !s.rate(6) && s.rate(4) && !s.rate(5))
  for f in 2...12{let (t,n)=s.begin()!;precondition(n==f && s.finish(t) && s.rate(3))}
  precondition(s.nextFixture==nil && s.begin()==nil && s.attempts.count==13)
  let limit=TrialVoiceSurvey();for _ in 0..<3{precondition(limit.begin() != nil);limit.cancel()};precondition(limit.begin()==nil)
  let stopped=TrialVoiceSurvey();let (t,_)=stopped.begin()!;precondition(stopped.finish(t));stopped.cancel();precondition(!stopped.rate(5) && stopped.begin() != nil)
  print("Survey stale/duplicate callbacks, interruption, rating bounds and retry limits PASS; no audio.")
 }
}
