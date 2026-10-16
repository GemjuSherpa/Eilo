# VC-INBOX-01 — sealing composition review

Review outcome: **NOT_APPROVED_FOR_IMPLEMENTATION**. The threat model and candidate standard
APIs are recorded; locked inbox encryption/import remains blocked. No inbox bytes are written.
This is not an independent cryptographic audit or evidence of secure physical key storage.

## Required boundary

A locked writer may hold only a public recipient key. The private recipient material must be
wrapped by a device-only, unlocked/authenticated platform key; neither its plaintext nor an
unwrapped symmetric database key may survive lock. Public-key substitution must fail via an
authenticated, versioned recipient-key identity bound to the local store generation. Authenticated
unlock is required for import/decryption; unlock alone never grants access. The database wrapping
APIs in VC-KEY-01/02 are not a sealed-inbox construction: their secret-key use is forbidden locked.

## Candidate and unresolved decisions

Use a vetted RFC9180 HPKE implementation, with explicit ciphersuite/version/KEM/KDF/AEAD and
recipient identity. Apple's CryptoKit exposes HPKE sender/recipient and authenticated associated
data; Google Tink documents an RFC9180 hybrid primitive. Exact Android platform API availability
and/or a pinned, licensed Tink dependency, interoperable envelope encoding and vendor compatibility
must be established before selection. No new dependency or handwritten KEM/key schedule is added.

Define a versioned envelope with bounded payload and AAD covering schema, recipient/store/key
version, record UUID and consent epoch. Use the implementation's nonce/key schedule; never reuse
sender contexts across crash/restart or synthesize nonce rules. Keep replay detection, consent
association and import idempotency in an authenticated transaction. A ciphertext integrity check
alone does not prevent replay, wrong-store import or forged public-key publication.

Required review/test vectors before approval: sender→recipient interoperability; tampered AAD,
encapsulated key, payload and tag; wrong recipient/store/key version; truncation/oversize; duplicate
record; key rotation/reset; crash between sealed write and atomic rename and during import;
post-lock stale callback; quota/disk-full; backup/transfer exclusion and passcode removal. Reject
unsupported versions instead of silently falling back. Public metadata must omit personal text.

A later reviewed implementation must use app-private atomic files, excluded backups, protected
metadata and bounded quotas; deletion of old keys/inboxes and orphan cleanup need lifecycle review.
Neither permitted screen-off audio nor the S08 feasibility/memory gate is changed by this design.

## Primary references

- [Apple HPKE](https://developer.apple.com/documentation/cryptokit/hpke)
- [Apple authenticated sealing](https://developer.apple.com/documentation/cryptokit/hpke/sender/seal(_:authenticating:))
- [Google Tink hybrid encryption](https://developers.google.com/tink/hybrid)
- [Tink wire format](https://developers.google.com/tink/wire-format)
- [RFC9180](https://www.rfc-editor.org/rfc/rfc9180)

The review can proceed in this sprint; acceptance of a selected composition remains blocked by
these unresolved requirements. S11 inbox implementation must not infer approval from this document.
