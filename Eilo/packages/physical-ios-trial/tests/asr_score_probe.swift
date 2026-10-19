import Foundation
@main struct ScoreProbe {
 static func main(){
  precondition(TrialAsrScore.words("It's 42, café!")==["it's","42","caf"])
  let tests=[("a b","a c",1,0,0),("a b","a",0,1,0),("a","a b c",0,0,2),("a b","b a",2,0,0),("abc","",0,1,0),("", "a",0,0,1)]
  for(r,h,s,d,i) in tests{let a=TrialAsrScore.edits(r,h);precondition(a["substitutions"]==s && a["deletions"]==d && a["insertions"]==i && a["errors"]==s+d+i)}
  print("Frozen ASR normalization/edit accounting PASS; no native inference or capture.")
 }
}
