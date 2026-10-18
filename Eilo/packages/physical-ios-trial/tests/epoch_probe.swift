import Foundation

@main struct EpochProbe {
  static func main(){
    let gate=TrialEpoch();let pending=gate.begin();var publications=0
    let oldCallback={if gate.current(pending){publications+=1}}
    gate.cancel();oldCallback();precondition(publications==0)
    let replacement=gate.begin();oldCallback();precondition(publications==0 && gate.current(replacement))
    if gate.current(replacement){publications+=1};precondition(publications==1)
    gate.cancel();precondition(!gate.current(replacement))
    print("Trial queued callback Stop/replacement/lock revocation PASS; no OS operations.")
  }
}
