# Start here

This is a candidate source tree, not a completed public release. Do not install it into a live home until the [capability gates](CAPABILITY-STATUS.md), legal/public source bindings and independent exact-byte reviews pass.

1. Read [the system overview](bible/01-system.md) and [setup choices](bible/02-setup-choice.md).
2. Select a supported release and verify source/asset checksums and notices. This candidate currently has factory-only source acquisition for required custom components; no public installer is represented as complete.
3. Follow [isolated installation](bible/03-installation.md) without inherited auth, activation, aliases or Gateway changes. Run the released payload's tests before using a real owner home.
4. Keep a private non-secret form outside the clone. Review [variables](templates/VARIABLES.md) and two unrelated [fictional examples](../examples/fictional-personal-assistant/customization.json). Validation is available; guarded seed rendering remains pending.
5. Preserve existing identity/memory and vault. For a new vault only, use [create-once setup](bible/07-knowledge.md); do not create another vault over existing knowledge.
6. The owner alone supplies model/platform credentials via native setup. Record real [model](bible/04-models.md) and [messaging](bible/17-messaging.md) acceptance separately.
7. Start bounded work through the [native lifecycle](bible/11-native-lifecycle.md), then require [independent verification/review](bible/13-review.md).
8. Exercise [private restore/update](bible/22-updates.md), follow the [handoff checklist](bible/21-handoff.md) and explicitly accept the exact release.

[Agent Bible](AGENT-BIBLE.md) · [Worked workflows](WORKED-WORKFLOWS.md) · [Command/source matrix](COMMAND-MATRIX.md)
