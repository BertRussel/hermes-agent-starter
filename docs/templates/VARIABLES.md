# Customization variables

The [schema](customization.schema.json) describes non-secret data, not instructions or permission grants. The [validator](../../scripts/validate_customization.py) returns normalized data without modifying caller input, writing personalized files, installing a profile, or echoing owner fields to logs. Example paths and model IDs are explicitly fictional; validation is not proof that a provider model exists or is authenticated.

| Field | Constraint | Responsibility |
| --- | --- | --- |
| AGENT_NAME | required, 1–80 characters | display identity, not native assignee |
| AGENT_INSPIRATION | optional, 0–160, defaults blank | style reference only; no literal impersonation or authority |
| OWNER_NAME | required, 1–80 | owner-approved display identity |
| AGENT_PURPOSE | required, 1–500 | bounded purpose, not delegated permissions |
| COMMUNICATION_STYLE | concise, balanced, detailed | presentation selection |
| TIMEZONE | valid IANA identifier, 1–100 | explicit owner selection |
| KNOWLEDGE_ROOT | absolute non-traversing, no symlinks, 2–4096 | private owner-selected destination |
| MODEL_PROVIDER | openrouter | currently validated non-secret configuration route; no universal provider claim |
| MODEL_ID | 1–160, restricted identifier alphabet | owner-selected model; runtime availability separately verified |
| AUTHORITY_POLICY | local-only, default local-only | closed independent policy; identity never expands it |

Unexpected fields, control characters, surrounding whitespace, template delimiters and malformed paths are rejected. Values are never evaluated by a shell or template expression engine. Keep your form outside the public clone; do not include tokens, passwords, conversation history, speculative owner facts or private client knowledge.

Run `python3 -B scripts/validate_customization.py /absolute/private/customization.json` from the clone. Expected result is JSON status `validated`, authority `local-only`, installed `false`. Failure exits 1 with the rejected field class. Independently verify the schema and normalized data through `tests/release/test_generic_customization.py`; a successful validation does not mean private Soul/USER/MEMORY seeds have been rendered or approved. Those seed templates and native import acceptance remain pending guarded implementation. Do not attempt to use an unresolved template as a live identity.

Upgrades must preserve private identity, memory and vault data. Native distribution update overwrites distribution-owned SOUL.md; do not update a personalized owner Soul without a reviewed backup, explicit identity preservation plan and independent post-update hash checks.
