# VC-PACK-10 — Distribution privacy review

Reviewed on 6 October 2026. Result: **production hosting blocked**, with review requested from Gemju Sherpa. No endpoint/CDN has been provisioned, no model uploaded and no release key configured. Local conversion and synthetic installer tests can proceed without approving end-user hosting.

| Candidate | Evidence | Decision |
| --- | --- | --- |
| Hugging Face official model source | [Privacy policy](https://huggingface.co/privacy), sections 1C and 4B, says service/session/IP/device information is collected and retained for service, security and legal purposes. No exact no-access-history configuration or retention exception was verified. Build downloads redirected to signed CDN URLs; this is source acquisition, not an approved mobile distribution path. | Allowed official build input; blocked as production distribution under the current no-retained-access-history requirement. |
| GitHub release assets | No Eilo model release or origin/CDN logging configuration exists. Public repository availability does not prove asset-delivery retention controls. | Not selected; unknown hosting retention blocks release. |
| Vercel/other origin/CDN | No model origin or CDN configuration exists and no provider logs/retention evidence has been obtained. | Not selected; no provisioning or spending. |

The app's production trust/license approvals and origin list remain empty. Synthetic test origins are not shipping endpoints. HTTPS requests contain a generic asset URL, fixed generic User-Agent and optional generic Range/If-Range metadata only. No cookies, account/device identifier, transcript, microphone bytes or personal context is accepted. HTTP logs/retention outside the app cannot be disabled by its downloader. Provider exposure includes network source IP even without an account.

Before production hosting can pass, select an origin/CDN and inspect its **actual** access, WAF, load-balancer, error, analytics, tracing, storage and backup logs. Record fields, retention/deletion, security exceptions and provider subprocessors; verify no retained per-user access history. Supply configuration/export evidence and a synthetic traffic test. If that policy is infeasible, Gemju Sherpa must review an explicit requirement change; a free tier or unsupported anonymity claim does not waive it.

This task records a completed review with a blocking result. It is not a passed hosting gate or release authorization. Physical traffic inspection, actual origin configuration and provider-specific retention verification are NOT RUN because there is no configured production host.
