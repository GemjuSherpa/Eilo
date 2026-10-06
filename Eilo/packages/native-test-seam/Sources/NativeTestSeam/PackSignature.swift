import Foundation
import CryptoKit
public struct VerifiedPack: Sendable {
  public let manifest: PackManifest
  public let keyID: String
  public let signedPayload, signatureBytes: Data
  public var digest: String { SHA256.hash(data:signedPayload).map { String(format:"%02x",$0) }.joined() }
  public static func verify(payload: Data, signature: Data, keyID: String, algorithm: String, trust: [String:Data], runtime: String, ios: Int=18) throws -> VerifiedPack {
    guard algorithm=="ES256", keyID.range(of:"^[a-z0-9-]{1,64}$",options:.regularExpression) != nil,
      (1...65536).contains(payload.count), (8...72).contains(signature.count), let encoded=trust[keyID] else { throw PackFailure.signature }
    do {
      let key=try P256.Signing.PublicKey(derRepresentation:encoded), sig=try P256.Signing.ECDSASignature(derRepresentation:signature)
      guard key.isValidSignature(sig,for:payload) else { throw PackFailure.signature }
    } catch { throw PackFailure.signature }
    return VerifiedPack(manifest:try PackManifest.parse(payload,runtime:runtime,ios:ios),keyID:keyID,signedPayload:payload,signatureBytes:signature)
  }
  private init(manifest: PackManifest,keyID: String,signedPayload: Data,signatureBytes: Data) { self.manifest=manifest;self.keyID=keyID;self.signedPayload=signedPayload;self.signatureBytes=signatureBytes }
}
