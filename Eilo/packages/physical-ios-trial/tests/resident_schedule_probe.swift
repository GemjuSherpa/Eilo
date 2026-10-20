import Foundation
@main struct ResidentScheduleProbe {
  static func main(){
    let groups=TrialResidentSchedule.groups
    precondition(groups.count==12 && groups.map{$0.index}==Array(1...12))
    for fixture in 1...6{
      let pair=Array(groups[(fixture-1)*2..<fixture*2])
      precondition(pair.map{$0.fixture}==Array(repeating:String(format:"compare-%02d",fixture),count:2))
      precondition(pair.map{$0.candidate}==(fixture%2==1 ? [0,1]:[1,0]))
    }
    precondition(groups.filter{$0.candidate==0}.count==6 && groups.filter{$0.candidate==1}.count==6)
    print("Resident schedule: all six fixtures, both exact candidate indices, balanced alternating group order PASS")
  }
}
