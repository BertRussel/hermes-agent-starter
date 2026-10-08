# Hermes setup on the VPS

This guide installs official Hermes on the prepared Ubuntu server, proves one command-line conversation, and stops before recipient customization or production automation.

Hermes changes frequently. Check the current official pages before running version-sensitive commands:

- [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation/)
- [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/)
- [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/)
- [Messaging](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/)

## 1. Use the intended service account

Install and run Hermes as the normal Linux user that will own it. Do not install it as root merely because the machine is a server.

Verify:

```bash
whoami
printf '%s\n' "$HOME"
pwd
```

The official POSIX source install normally uses:

- source: `~/.hermes/hermes-agent/`
- launcher: `~/.local/bin/hermes`
- user data: `~/.hermes/`

`HERMES_HOME` changes the user-data location. Do not delete the data home to repair application code.

## 2. Back up an existing installation

If `~/.hermes/` or an existing Hermes launcher is already present, stop and make a reviewed backup before installing or importing anything. Preserve identity, configuration, sessions, memory, profiles, and credentials according to their own privacy rules.

Never overwrite a living agent with this public starter.

## 3. Review the official installer

The official Linux command is:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

For a high-trust server, download and inspect the installer first instead of piping unseen bytes directly to a shell:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/hermes-install.sh
less /tmp/hermes-install.sh
bash /tmp/hermes-install.sh
```

The official installer clones the source, installs managed dependencies, creates the launcher, prepares the data directory, and normally enters interactive setup. Browser and computer-use components may be downloaded unless their documented skip options are selected.

Use only the current official installer and its documented flags. Do not install a private factory archive from this repository.

## 4. Reload the shell and verify the command

```bash
source ~/.bashrc
command -v hermes
```

If the command is not found, verify that `~/.local/bin` is on `PATH` and follow the installer’s reported recovery step.

Run the supported diagnostic:

```bash
hermes doctor
```

Resolve installation errors before adding profiles or messaging.

## 5. Configure one provider and model

Use the interactive setup rather than writing secrets into Markdown, shell history, Git, or chat:

```bash
hermes model
```

Or run the full wizard:

```bash
hermes setup
```

Provider credentials belong only in Hermes’ supported credential route or an explicitly approved provider-owned OAuth flow. Public templates, Brain OS, Git, chat, screenshots, and logs are not credential stores.

The selected model must satisfy Hermes’ current context requirements. The current official quickstart requires at least a 64K-token context window.

## 6. Prove a normal command-line conversation

Start Hermes:

```bash
hermes
```

Use a harmless, verifiable prompt such as:

```text
Tell me the current working directory and list the names of the files in it.
```

Success means:

- the intended provider and model load;
- Hermes answers without authentication or configuration errors;
- a permitted read-only tool can run;
- a second conversational turn works;
- the session can be resumed.

Exit, then verify session continuity:

```bash
hermes --continue
```

Do not add Discord, cron, profiles, browser access, or autonomous workflows until this base chat works.

## 7. Keep the public and private files separate

Create a private setup folder outside the public clone. Put only owner-reviewed generated files there:

```text
SOUL.md
USER.md
MEMORY.md
PRIVATE-AGENT-BIBLE.md
BOOTSTRAP-PROMPT.md
OWNER-INTAKE.md or the completed PDF
```

Generate them from the completed private Owner Intake and [`templates/`](templates/). Never edit the public templates in place with real owner information.

Before installation, review every rendered file for:

- unresolved placeholders;
- another person’s identity or paths;
- credentials or credential identifiers;
- private business or personal data that does not belong there;
- incorrect approval boundaries;
- machine facts that were guessed instead of discovered.

## 8. Install the primary identity carefully

The installed `SOUL.md` defines the primary agent’s identity and authority. Back up any existing Soul before replacement. Install only the exact owner-approved bytes through the supported route for the current Hermes release, then start a fresh session and verify that the live agent uses them.

A copied file is not proof of active identity.

Review `USER.md` and `MEMORY.md` separately. Memory should contain compact stable facts, not tasks, transcripts, secrets, or raw project state.

## 9. Prepare persistent gateway operation

Discord setup comes next. On a Linux VPS, the messaging gateway normally runs as the same service user. If it must survive logout, the official installation guide recommends enabling user lingering as an administrator:

```bash
sudo loginctl enable-linger "$USER"
```

Do not start, stop, restart, or install a production gateway until Discord is configured, the owner allowlist is correct, and the owner approves the lifecycle action.

## 10. Verify before moving on

Record non-secret evidence for:

- installation method and source identity;
- `hermes doctor` result;
- provider/model class without secret values;
- successful first chat;
- successful session resume;
- exact approved Soul/User/Memory hashes when installed;
- backup and rollback route;
- unresolved limitations.

Continue to [`DISCORD-SETUP.md`](DISCORD-SETUP.md). After Discord works, use the private rendered Bootstrap to complete the remaining Day 1 setup and acceptance stages.
