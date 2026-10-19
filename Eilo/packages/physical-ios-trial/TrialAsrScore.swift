import Foundation

/// Same frozen ASCII normalization and substitution/deletion/insertion tie order as quality_report.py.
enum TrialAsrScore {
  static func words(_ text:String)->[String]{
    let lower=text.lowercased(),regex=try! NSRegularExpression(pattern:"[a-z0-9]+(?:'[a-z]+)?")
    return regex.matches(in:lower,range:NSRange(lower.startIndex...,in:lower)).map{String(lower[Range($0.range,in:lower)!])}
  }
  static func edits(_ reference:String,_ hypothesis:String)->[String:Int]{
    let a=words(reference),b=words(hypothesis)
    var row=(0...b.count).map{(errors:$0,s:0,d:0,i:$0)}
    for (offset,x) in a.enumerated(){
      let n=offset+1;var next=[(errors:n,s:0,d:n,i:0)]
      for (j,y) in b.enumerated(){
        if x==y{next.append(row[j]);continue}
        let sub=row[j],del=row[j+1],ins=next[j]
        let candidates=[(errors:sub.errors+1,s:sub.s+1,d:sub.d,i:sub.i),(errors:del.errors+1,s:del.s,d:del.d+1,i:del.i),(errors:ins.errors+1,s:ins.s,d:ins.d,i:ins.i+1)]
        var best=candidates[0];for c in candidates.dropFirst() where c.errors<best.errors{best=c};next.append(best)
      };row=next
    }
    let r=row.last!;return["reference_words":a.count,"substitutions":r.s,"deletions":r.d,"insertions":r.i,"errors":r.errors]
  }
}
