# Native model pack contract

Schema 1 is bounded UTF-8 JSON (64 KiB maximum). It declares schema, packId, positive revision, exact runtimeRevision, minimum Android/iOS versions and 1–16 artifacts. Each artifact declares id, safe single-component filename, role, HTTPS URL without query/credentials/fragment, SHA-256, byte size, SPDX license and SHA-256 of license evidence. No escaped strings, unknown fields, duplicate keys, negative/fractional numbers or trailing commas. Generic ASCII metadata avoids parser differences. Manifests are signed over the exact bytes; JSON reserialization is never used for signature verification.

Runtime revisions must match exactly. Paths cannot traverse directories. Artifact IDs/filenames are unique, files are bounded to 8 GB and total pack size to 12 GB. License declarations are not legal clearance; complete source/license inventory and review remain necessary before pack inclusion.

VC-PACK-03: Kotlin compiler + 29 JUnit tests and Swift compiler + 29 XCTest tests passed locally, including schema rejection cases. Kotlin uses Android's platform org.json; the pinned JSON-java 20250517 test-only dependency supplies executable JVM parser tests. Physical Android parser/crypto behavior remains to be verified.

VC-PACK-04: ES256 (ECDSA P-256/SHA-256), DER signature and DER SPKI public key; native platform JCA/CryptoKit implementations only. Exact raw payload bytes are verified before parsing. Trust lookup is configured locally, never fetched from the manifest. Empty trust fails closed. Local test keys are generated in memory and are not shipping keys. Kotlin compiler/JUnit30 and Swift compiler/XCTest30 pass for valid signatures, tampering, unknown key, unsupported algorithm and empty production trust. Physical Android JCA remains unverified.
