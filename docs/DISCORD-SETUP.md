# Private Discord setup for Hermes

This guide creates a private Discord server for communicating with one owner-operated Hermes agent. It follows the current [official Hermes Discord guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord).

The bot token is a credential. Never paste it into chat, Git, Obsidian, setup notes, screenshots, or ordinary shell commands. Enter it only through the supported interactive setup or approved secret route.

## 1. Create the private server

In Discord:

1. Select **Add a Server → Create My Own**.
2. Give it a clear private name.
3. Do not enable Community, Discovery, public invites, or public onboarding.
4. Keep membership owner-only during setup.
5. Enable MFA on the owner’s Discord account.

A simple initial channel layout is enough:

```text
START HERE
  #welcome
AGENT
  #agent
  #agent-logs
PROJECTS
  #projects
```

Start with one operating channel. Add channels only when they solve a real routing need.

## 2. Create a Discord application

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select **New Application**.
3. Name it after the agent or its role.
4. Accept Discord’s terms and create it.
5. Record the non-secret Application ID if needed for invitation setup.

## 3. Configure the bot

Open **Bot** in the application:

1. Customize the bot name and avatar if desired.
2. Leave **Require OAuth2 Code Grant** off.
3. For the smallest private setup, Public Bot may remain off and the manual invite route may be used. If the official wizard requires a temporary public-bot invitation route, enable it only long enough to invite the bot, then review the final setting.
4. Under **Privileged Gateway Intents**, enable:
   - **Server Members Intent**
   - **Message Content Intent**
5. Leave Presence Intent off unless a real feature requires it.
6. Save changes.

Hermes requires Message Content Intent to receive message text. The current official guide also requires Server Members Intent for member resolution and owner allowlisting.

## 4. Create and protect the token

On the Bot page, create or reset the bot token. Discord may show it only once.

- Store it in the owner’s approved password/secret manager.
- Do not send it to another person.
- Do not place it in the Owner Intake.
- Do not commit it to the repository.
- If it is exposed, reset it immediately and replace the saved credential.

## 5. Invite the bot with minimum permissions

The official Hermes wizard can verify the token and print an invitation link. Alternatively, configure a Guild Install with these scopes:

- `bot`
- `applications.commands`

Minimum text permissions:

- View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History

Add these only if using threads/reactions:

- Create Public Threads
- Send Messages in Threads
- Add Reactions

Do not grant Administrator. Voice permissions are unnecessary unless voice-channel operation is deliberately enabled later.

Open the generated invitation URL, choose the private server, authorize it, and complete Discord’s human verification if requested.

## 6. Restrict the server channels

Create a dedicated bot role if useful. For channels the agent should not access, explicitly deny **View Channel**. Confirm the bot can see only its intended channels.

For the initial owner-only server:

- do not create reusable public invite links;
- remove unexpected members and integrations;
- restrict `@everyone` from managing channels, roles, webhooks, or the server;
- keep role mention and `@everyone` mention permissions disabled for the bot unless explicitly needed.

## 7. Configure Hermes interactively

On the VPS, run:

```bash
hermes gateway setup
```

Choose **Discord** and enter the token only when the wizard requests it. The current wizard verifies the token, checks privileged intents, prints an invite link, and offers to allowlist the bot owner.

Prefer an exact Discord user ID for the allowlist. The official guide permits usernames, but IDs are stable and unambiguous.

Do **not** enable allow-all access. Keep the initial allowlist owner-only.

## 8. Choose channel behavior

Current Hermes defaults are safe for a private server:

- DMs receive normal replies.
- Server channels require an `@mention` by default.
- Threads keep separate session history.
- Shared channels isolate sessions per user by default.

For one dedicated owner-only `#agent` channel, you may later make that exact channel mention-free. Do not disable mention requirements globally across a server without understanding the effect.

Set a home channel only after the exact target channel is confirmed. The home channel is where proactive reminders and automation output may be delivered, so it should not be a public or noisy channel.

## 9. Start and test the gateway

Starting or installing a persistent gateway is an external lifecycle action. Do it only after configuration and owner approval.

Use the current official gateway command shown by the installed Hermes help. Then test from Discord:

1. Confirm the bot becomes online.
2. In the intended private channel, mention it and send a harmless message.
3. Confirm it replies in the expected channel or thread.
4. Send a second message to verify conversational continuity.
5. Confirm a non-allowlisted test account cannot use it, if a safe test account is available.
6. Confirm the bot cannot see a channel outside its intended scope.
7. Send a harmless file and verify receipt only if attachment handling is required.

A successful REST or token check is not proof that live Discord Gateway messages work. Require a real inbound-and-outbound message round trip.

## 10. Troubleshooting

### Bot is offline

- Confirm the gateway process/service is running.
- Re-run `hermes gateway setup` if the token or adapter was not configured.
- Check the current Hermes gateway status and logs without exposing the token.

### Privileged intents error

Return to Developer Portal → Application → Bot and enable both Server Members Intent and Message Content Intent. Save changes, then restart through the approved external lifecycle route.

### Bot is online but silent

Check:

- the owner is on the Hermes allowlist;
- the message mentions the bot where mentions are required;
- the bot has View Channel, Send Messages, and Read Message History;
- the channel is not explicitly denied by Discord role overrides;
- the configured token belongs to the application that was invited.

### Wrong people can interact

Stop the gateway, correct the allowlist and Discord role/channel permissions, then verify with an unauthorized account before restoring normal use. Authentication to Discord does not authorize every server member.

## 11. Acceptance checklist

- [ ] Server is private and owner-controlled.
- [ ] Owner account has MFA.
- [ ] Bot token is stored only in the approved secret route.
- [ ] Message Content and Server Members intents are enabled.
- [ ] Bot has no Administrator permission.
- [ ] Bot can see only intended channels.
- [ ] Hermes allowlist is owner-only or explicitly approved.
- [ ] Real private message round trip passed.
- [ ] Mention, thread, and channel behavior match the intended design.
- [ ] Non-allowlisted access is denied.
- [ ] Home-channel routing is either verified or intentionally unset.

After this passes, use the private rendered Bootstrap to establish Brain OS, specialist profiles, backup, and acceptance evidence.
