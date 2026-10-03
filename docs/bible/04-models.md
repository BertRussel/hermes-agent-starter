# 4. Models and credentials

## Actor and authority
The owner authenticates to providers and approves spending. Workers cannot copy another profile's authentication, open accounts or infer permission from available credentials.

## Prerequisites and version
Use native provider setup on the accepted runtime. The customization validator currently accepts the non-secret OpenRouter configuration route only; this is not a claim that every model ID exists or that other native providers are unsupported.

## Inputs
Chosen provider/model, price limits, owner-approved secret route, expiry/revocation policy and per-role model overrides where explicitly reviewed.

## Procedure
Run native `hermes model` or the owner-operated setup wizard in the intended private profile. Supply credentials through the documented provider/credential interface, never the customization JSON, Git, Bible or chat transcript. Verify provider and model selection before a harmless bounded inference. Set turn/resource limits and observe actual usage. Keep formal review attribution separate even when multiple roles use the same model. If using a secret manager, authorize only the registered website/account scope; available secret access does not authorize unrelated business action.

## Expected results
A real inference returns genuine output with recorded provider/model and bounded usage. Before that test, status is configured or prepared, not connected or accepted. Do not fabricate answers as a canary.

## Independent verification
A separate owner-approved observer verifies the result and redacted usage record. Check that disposable packaging environments contain no inherited provider keys; unit tests enforce the scrubbed environment.

## Failure and recovery
Expired credentials, rate limits and unavailable models are individual gates. Stop retries at the documented limit; let the owner reauthenticate or select a supported alternative without printing secret values.

## Privacy and outputs
Authentication belongs in native private credential storage. Retain only redacted outcome/usage references in the acceptance record.

## Sources
[Isolation tests](../../tests/release/test_full_system_package.py), [official providers](https://hermes-agent.nousresearch.com/docs/integrations/providers), [security](06-security.md).
