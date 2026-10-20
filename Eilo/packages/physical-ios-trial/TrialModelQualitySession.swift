import Foundation

/// Main-thread fixed-fixture quality review. Generation permits a rating; it cannot supply one.
final class TrialModelQualitySession {
  struct Attempt {let fixture:Int,ticket:UUID;var status="GENERATING",rating:Int?}
  private(set) var attempts:[Attempt]=[]
  private var pending:UUID?
  var awaitingRating:Bool{guard let p=pending,let a=attempts.last else{return false};return a.ticket==p && a.status=="GENERATED"}
  var nextFixture:Int?{(1...6).first{f in !attempts.contains{$0.fixture==f && $0.rating != nil}}}
  func begin()->(UUID,Int)?{
    guard pending==nil,let fixture=nextFixture,attempts.filter({$0.fixture==fixture}).count<3 else{return nil}
    let ticket=UUID();attempts.append(Attempt(fixture:fixture,ticket:ticket));pending=ticket;return(ticket,fixture)
  }
  @discardableResult func finish(_ ticket:UUID)->Bool{
    guard pending==ticket,let i=attempts.indices.last,attempts[i].ticket==ticket,attempts[i].status=="GENERATING" else{return false}
    attempts[i].status="GENERATED";return true
  }
  @discardableResult func fail(_ ticket:UUID)->Bool{
    guard pending==ticket,let i=attempts.indices.last,attempts[i].ticket==ticket,attempts[i].status=="GENERATING" else{return false}
    attempts[i].status="FAILED";pending=nil;return true
  }
  @discardableResult func rate(_ score:Int)->Bool{
    guard (1...5).contains(score),awaitingRating,let i=attempts.indices.last else{return false}
    attempts[i].rating=score;pending=nil;return true
  }
  func cancel(){
    if let p=pending,let i=attempts.indices.last,attempts[i].ticket==p{attempts[i].status="CANCELLED"}
    pending=nil
  }
  var aggregate:[[String:Any]]{attempts.enumerated().map{i,a in
    var row:[String:Any]=["fixture_id":String(format:"compare-%02d",a.fixture),"attempt":i+1,"model_status":a.status]
    if let rating=a.rating{row["rubric_quality"]=rating};return row
  }}
}
