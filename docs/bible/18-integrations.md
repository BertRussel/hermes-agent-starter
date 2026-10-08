# 18. Tools and integrations

## Actor and authority
The owner approves integrations, accounts and business scope. The agent uses only enabled tools and reviewed source rights; tool presence never grants account authority.

## Prerequisites and version
Record actual tool/backend version, installation route, credential needs and supported platform. A profile tool allowlist is not a filesystem/network sandbox.

## Inputs
Capability inventory, documented service endpoint, approved identity/scope, resource limits, harmless canary and recovery/uninstall plan.

## Procedure
Inspect actual manifests/imports and native help before configuring an integration. Keep secrets separate from non-secret settings. Register MCP through native routes and test only the authorized server/tool selection. For browser work, verify the intended backend and authenticated identity; do not infer that unavailable Chromium means every browser route is unavailable. For file/terminal tools, bind exact sources/outputs and run real builds. For documents, reopen generated DOCX/XLSX/PDF/raster formats; formula presence is not calculated-workbook acceptance. For research/media, distinguish local fixture parsing/encoding from external service or model operation. Remove unused integrations through supported owner-approved commands, preserving private data.

### Browser selection, authentication and owner assistance

Choose public extraction for static research, a verified native browser backend
for interactive/JavaScript pages, or an approved attached browser/desktop for
native dialogs. Inventory the recipient's actual backend, version, registered
domains and readiness before acting. Test a harmless public page and then the
permitted read-only operation. A factory CDP/noVNC deployment is not a recipient
installation; unavailable Chromium does not prove all alternatives unavailable.
The bounded HTTPS reference reader is research, not a JavaScript browser.

Inspect the live URL, redirects, rendered page and existing field state before
authentication. Reuse a valid registered session and verify its account label
privately. Routine registered-session recovery is authorized within the approved
domain/account/task, not post-login action authority. Unregistered access or
a changed identity requires review; a login redirect alone is not universal failure.

Login/runtime secrets come only from recipient-owned Bitwarden Secrets Manager
(BWS) through the approved controlled in-memory route to verified registered
fields. Verify this injection route on the recipient installation; if absent,
report that gate. Never use browser-stored autofill, saved passwords or
Hermes/browser vaults as credential sources, or duplicate BWS secrets into them.
Disable credential saving through supported browser policy. Do not place values
in tool arguments, terminal commands, scripts, clipboard, files, logs or chat.
Explicitly registered provider-owned OAuth is separate, not a password fallback.

For MFA/TOTP, use only an approved in-memory challenge path; never expose a code
or seed. A passkey, device/hardware prompt or app approval belongs to the actual
authorized holder. Stop for the owner when required; do not bypass CAPTCHA,
unregistered MFA or new consent. Authentication proves access only; publication,
sends, payments, account changes and destructive/production actions retain
their separate exact authority.

Owner assistance includes the safe direct page URL (strip sensitive tokens),
site/account label (non-secret alias), current step, blocker, expected action,
expiry (or unknown) and post-action verification. A private browser-access link
may be used only after verifying its actual supported mechanism, authorization,
expiry and recipient reachability. That mechanism is currently not verified in the recipient environment;
no generic browser-link mechanism is supplied. Give the direct safe URL and
explain if the owner must open their own session; never publish a CDP endpoint.
After owner action, refresh the live page, verify intended account and expected
read-only state, and resume only the original task scope. Chat acknowledgement
alone is not verification.

Separate expired session, rejected BWS, missing injection route, human challenge
and backend outage. Reject suspicious redirects/account drift; bound retries
instead of guessing credentials. Keep secrets and secret-bearing screenshots
out of chat and durable evidence. Recover only through the registered route.

## Expected results
Each capability has source/license, dependencies, tested platform, health result, real canary, limits and known unexercised routes. No universal browser/model/service claim appears.

## Independent verification
Rebuild required supporting environments from pinned sources/dependencies and run actual canaries on extracted bytes. Verify network/API writes by exact target readback, not simulated responses.

## Failure and recovery
Keep auth/credential failures separate from package/import/backend failures. Use documented safe alternatives, limit retries and return a precise gate if access is unavailable. Never disable security or inherit live auth to make a fixture pass.

## Privacy and outputs
Retain redacted capability records privately; no account dumps, browser sessions or token-bearing logs in the release.

## Sources
[Supporting implementation](../../runtimes/supporting-runtime/src/supporting_runtime/runtime.py), [tests](../../tests/release/test_supporting_runtime.py), [official MCP](https://hermes-agent.nousresearch.com/docs/).
