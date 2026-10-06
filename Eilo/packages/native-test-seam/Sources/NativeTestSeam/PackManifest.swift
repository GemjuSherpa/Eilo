import Foundation
import CoreFoundation
public struct PackArtifact: Equatable, Sendable {
  public let id, filename, role, url, sha256, license, licenseEvidence: String
  public let bytes: Int64
}
public struct PackManifest: Equatable, Sendable {
  public let packID, runtimeRevision: String
  public let revision: Int64
  public let minAndroid, minIOS: Int
  public let artifacts: [PackArtifact]
  static let header: Set<String> = ["schema","packId","revision","runtimeRevision","minAndroid","minIos","artifacts"]
  static let fields: Set<String> = ["id","filename","role","url","sha256","bytes","license","licenseEvidence"]
  public static func parse(_ payload: Data, runtime: String, ios: Int = 18) throws -> PackManifest {
    func check(_ valid: Bool) throws { if !valid { throw PackFailure.manifest } }
    func text(_ o: [String: Any], _ k: String) throws -> String { guard let s=o[k] as? String else { throw PackFailure.manifest }; return s }
    func number(_ o: [String: Any], _ k: String) throws -> Int64 {
      guard let n=o[k] as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID(), ["i","q"].contains(String(cString:n.objCType)) else { throw PackFailure.manifest }; return n.int64Value
    }
    func matches(_ s: String, _ pattern: String) -> Bool { s.range(of:"^(?:"+pattern+")$",options:.regularExpression) != nil }
    try check((1...65536).contains(payload.count))
    guard let raw=String(data:payload,encoding:.utf8), let o=try JSONSerialization.jsonObject(with:payload) as? [String:Any] else { throw PackFailure.manifest }
    try check(raw.range(of:#"^(?:[{}\[\]:,]|"[\x20-\x21\x23-\x5b\x5d-\x7e]*"|[0-9]+|[ \t\r\n])+$"#,options:.regularExpression) != nil && raw.range(of:",\\s*[}\\]]",options:.regularExpression)==nil)
    try check(Set(o.keys)==header && number(o,"schema")==1)
    let id=try text(o,"packId"), revision=try number(o,"revision"), rr=try text(o,"runtimeRevision")
    try check(matches(id,"[a-z0-9][a-z0-9-]{0,63}") && (1...9007199254740991).contains(revision) && matches(rr,"[a-f0-9]{40}") && rr==runtime)
    let a=try number(o,"minAndroid"), i=try number(o,"minIos")
    try check((35...99).contains(a) && i >= 18 && i <= Int64(ios))
    guard let files=o["artifacts"] as? [[String:Any]] else { throw PackFailure.manifest }; try check((1...16).contains(files.count))
    let artifacts=try files.map { f -> PackArtifact in
      try check(Set(f.keys)==fields)
      let id=try text(f,"id"), name=try text(f,"filename"), role=try text(f,"role"), url=try text(f,"url")
      try check(matches(id,"[a-z0-9][a-z0-9-]{0,63}") && matches(name,"[a-z0-9][a-z0-9_-]{0,95}\\.(gguf|onnx|json|txt)") && ["llm","asr","wake","vad","license","tokenizer"].contains(role))
      guard let u=URLComponents(string:url), let path=URL(string:url) else { throw PackFailure.manifest }
      try check(url.utf8.count<=2048 && u.scheme=="https" && u.host != nil && u.user==nil && u.password==nil && u.query==nil && u.fragment==nil && (u.port==nil || u.port==443) && !u.percentEncodedPath.contains("%") && !u.path.contains("\\") && path.standardized.absoluteString==url)
      let hash=try text(f,"sha256"), evidence=try text(f,"licenseEvidence"), bytes=try number(f,"bytes"), license=try text(f,"license")
      try check(matches(hash,"[a-f0-9]{64}") && matches(evidence,"[a-f0-9]{64}") && (1...8_000_000_000).contains(bytes) && ["Apache-2.0","MIT","BSD-3-Clause","CC0-1.0"].contains(license))
      return PackArtifact(id:id,filename:name,role:role,url:url,sha256:hash,license:license,licenseEvidence:evidence,bytes:bytes)
    }
    try check(Set(artifacts.map(\.id)).count==artifacts.count && Set(artifacts.map(\.filename)).count==artifacts.count && artifacts.reduce(Int64(0)) { $0+$1.bytes }<=12_000_000_000)
    let regex=try NSRegularExpression(pattern:"\"([^\"\\\\]*)\"\\s*:")
    let keys=regex.matches(in:raw,range:NSRange(raw.startIndex...,in:raw)).map { String(raw[Range($0.range(at:1),in:raw)!]) }
    try check(keys.count==header.count+fields.count*artifacts.count && header.allSatisfy { key in keys.filter { $0==key }.count==1 } && fields.allSatisfy { key in keys.filter { $0==key }.count==artifacts.count })
    return PackManifest(packID:id,runtimeRevision:rr,revision:revision,minAndroid:Int(a),minIOS:Int(i),artifacts:artifacts)
  }
}
public enum PackFailure: Error { case manifest, signature, origin, transport, cancelled, integrity, activation, unavailable }
