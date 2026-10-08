# Oracle Cloud VPS setup

This guide creates an economical always-on Ubuntu server suitable for a personal Hermes agent. Oracle’s limits and console labels can change; verify every resource is marked **Always Free-eligible** before creating it.

**Current official references:**

- [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Create a compute instance](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm)
- [Manage Linux SSH keys](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/managingkeypairs.htm)
- [Connect to a Linux instance](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm)

## What the current allowance means

Oracle’s June 12, 2026 documentation states that an Always Free tenancy provides, in its home region:

- up to **2 Ampere A1 OCPUs and 12 GB RAM total** using `VM.Standard.A1.Flex`;
- **200 GB total** combined boot and block-volume storage;
- up to five Always Free volume backups;
- 20 GB of Object Storage in an Always Free-only account;
- 10 TB monthly outbound data transfer.

The default boot volume is 50 GB and counts against the 200 GB total. A practical single-server layout is one A1 instance with 2 OCPUs, 12 GB RAM, and a boot volume sized for the real workload. Do not allocate all available storage without leaving a deliberate backup and recovery plan.

Always Free A1 capacity can be temporarily unavailable. Oracle recommends trying another availability domain or waiting. Do not upgrade or create paid resources merely to bypass a temporary capacity message unless the owner deliberately accepts possible charges.

Oracle may reclaim an Always Free compute instance it classifies as idle. Keep independent backups; do not manufacture load to defeat the policy.

## 1. Create and secure the Oracle account

The owner should:

1. Create the Oracle Cloud account in their own legal identity.
2. Complete billing verification and MFA privately.
3. Choose the **home region** carefully. Always Free compute and block volumes must be created there, and the home region is a durable tenancy choice.
4. Record the account-recovery route in the owner’s approved password manager.
5. Do not send passwords, MFA codes, payment details, recovery codes, cookies, or account exports to the setup agent.

Creating an account may require a payment card for identity verification. “Always Free” is not a promise that every possible resource is free. The owner remains responsible for checking the console’s cost estimate and resource labels.

## 2. Create an SSH key on the owner’s computer

Use an existing securely managed key or create a dedicated Ed25519 key:

```bash
ssh-keygen -t ed25519 -a 64 -f ~/.ssh/hermes_oracle
```

Protect the private key. Only the `.pub` public key is uploaded to Oracle.

On Linux or macOS:

```bash
chmod 600 ~/.ssh/hermes_oracle
```

Back up the private key through the owner’s approved encrypted recovery route. Never commit it to Git or paste it into chat.

## 3. Create the network

In the Oracle Console:

1. Open **Networking → Virtual Cloud Networks**.
2. Use **Start VCN Wizard → Create VCN with Internet Connectivity**.
3. Create one VCN with a public subnet for the first server.
4. Ensure the route table has an Internet Gateway route.
5. Restrict inbound SSH (`TCP 22`) to the owner’s current public IP/CIDR when practical. Avoid `0.0.0.0/0` for SSH.
6. Do not open Hermes, database, admin, or development ports to the public internet. Use SSH tunnelling, a private overlay, or another reviewed private-access route later.

The cloud security list or Network Security Group and Ubuntu’s host firewall are separate controls. Traffic must be allowed by both when the firewall is enabled.

## 4. Create the instance

Open **Compute → Instances → Create instance** and set:

1. **Placement:** an availability domain in the home region.
2. **Image:** a current Ubuntu image marked Always Free-eligible.
3. **Shape:** `VM.Standard.A1.Flex`.
4. **Resources:** up to the currently documented total of 2 OCPUs and 12 GB RAM for the tenancy. For a single Hermes host, allocating the full free A1 allowance is the simplest layout when available.
5. **Networking:** the VCN and public subnet created above.
6. **Public IPv4:** enabled only because the first connection uses direct SSH. A private subnet plus Bastion is safer but more involved.
7. **SSH key:** upload or paste the public key only.
8. **Boot volume:** choose the required size deliberately. It counts against the 200 GB combined allowance.

Before selecting **Create**, confirm the page identifies the selected shape and storage as Always Free-eligible and shows no unexpected estimated charge.

## 5. Connect by SSH

Copy the public IP from the instance page. Ubuntu images use the `ubuntu` user:

```bash
ssh -i ~/.ssh/hermes_oracle ubuntu@SERVER_PUBLIC_IP
```

On first connection, verify the displayed host-key fingerprint against Oracle’s instance/console information before accepting it. Then save a local SSH alias if useful:

```sshconfig
Host hermes-vps
    HostName SERVER_PUBLIC_IP
    User ubuntu
    IdentityFile ~/.ssh/hermes_oracle
    IdentitiesOnly yes
```

Connect with:

```bash
ssh hermes-vps
```

## 6. Apply the minimum Ubuntu baseline

Run updates before installing applications:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y git curl ca-certificates tar unzip jq ufw fail2ban
sudo timedatectl set-timezone UTC
```

Enable a host firewall without locking out SSH:

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Then:

1. Confirm key-based SSH works in a second terminal before closing the first.
2. Disable password SSH login only after confirming the active image and recovery route.
3. Keep root SSH login disabled.
4. Enable automatic security updates if they are not already active.
5. Do not expose private services directly to the internet.

A reboot may be required after kernel updates:

```bash
sudo reboot
```

Reconnect and confirm the expected host.

## 7. Verify the server

Record only non-secret facts:

```bash
uname -a
uname -m
nproc
free -h
lsblk
findmnt /
df -h /
timedatectl
```

For Ampere A1, the architecture should be ARM64/AArch64. Software and containers must support that architecture.

Check that:

- CPU and memory match the selected shape;
- the root filesystem sees the intended boot-volume size;
- UTC is configured;
- SSH works using the owner’s key;
- only intended ports are reachable;
- no password, token, or private key was written into the project repository.

## 8. Storage and backup

The 200 GB allowance is shared by boot and block volumes. Choose one simple model:

- **Single larger boot volume:** fewer moving parts; easiest for one server.
- **50 GB boot plus attached data volume:** cleaner separation and easier data-volume replacement, but requires formatting, mounting, and tested mount recovery.

A volume existing in Oracle is not a backup. Keep at least one tested off-instance recovery copy of the public repository, private configuration, and approved Brain OS data. Exclude credentials unless the backup route is explicitly designed and encrypted for them.

## 9. Cost safeguards

Before leaving the console:

1. Open **Governance & Administration → Limits, Quotas and Usage**.
2. Confirm the instance, boot volume, attached volumes, and backups are within current Always Free allowances.
3. Create a budget and billing alert even if the expected cost is zero.
4. Delete unused paid trial resources before trial credits expire.
5. Recheck costs after resizing, adding backups, changing regions, or attaching storage.

## Ready for Hermes

Continue only when:

- SSH is reliable;
- system updates are complete;
- CPU, RAM, architecture, disk, and timezone were verified;
- inbound access is minimal;
- backup and recovery ownership are understood;
- the Oracle console shows no unintended paid resources.

Next: [`HERMES-SETUP.md`](HERMES-SETUP.md).
