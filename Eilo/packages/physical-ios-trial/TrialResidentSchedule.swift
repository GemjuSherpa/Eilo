import Foundation

/// Six frozen fixture groups; candidate order reverses at every fixture boundary.
enum TrialResidentSchedule {
  struct Group:Equatable{let index:Int,fixture:String,candidate:Int}
  static let groups:[Group]=(1...6).flatMap{fixture in
    let order=fixture%2==1 ? [0,1]:[1,0]
    return order.enumerated().map{offset,candidate in
      Group(index:(fixture-1)*2+offset+1,fixture:String(format:"compare-%02d",fixture),candidate:candidate)
    }
  }
}
