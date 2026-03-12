# LEARNING-001: Cron Git Push Authentication Failure

> **Date:** 2026-03-12
> **Severity:** HIGH — data pipeline works but delivery to production fails silently
> **Affected Agent:** Gimli (TRSbench / unified_ddp.py)
> **Detected by:** David (manual Telegram review) — should have been detected by Treebeard or Sauron
> **Resolution time:** ~30 minutes from diagnosis to verified fix
> **Status:** RESOLVED

---

## 1. Symptom — What Was Observed

At 4:49 AM CST on March 12, 2026, the Gimli DDP cron job fired and sent a Telegram notification:

```
TR2 Unified DDP starting
2026-03-12
LIVE
40 sources
```

Scraping completed successfully at 5:08 AM with all 10 pillars reporting data. However, the Telegram status message also contained:

```
JSON updated but push failed.
```

The live site (solosevn.github.io/TR2/) was still showing March 11 data. GitHub commits page showed no March 12 commit from TRSdavid.

**Key observation:** The scraper ran perfectly. The data was produced. The ONLY failure was the `git push` step — the final delivery to production.

---

## 2. Diagnosis — Root Cause Analysis

### What we checked (in order):

1. **GitHub commits page** — No March 12 commit from TRSdavid. Last commit was March 11 at 5:15 PM. This confirmed the push failed, not the scraper.

2. **Telegram message** — The script's own error reporting said "JSON updated but push failed." The script correctly diagnosed itself.

3. **Git remote configuration** — The TR2 repo was configured with an HTTPS remote:
   ```
   origin  https://github.com/solosevn/TR2.git
   ```

4. **How HTTPS auth works on macOS** — When you `git push` via HTTPS from Terminal, macOS Keychain provides your GitHub credentials transparently. You never see a password prompt because the credential helper (`git credential-osxkeychain`) retrieves it from Keychain.

5. **Why cron fails** — Cron jobs (and launchd agents) run in a stripped-down environment. They do NOT have access to:
   - macOS Keychain (requires user session/GUI context)
   - SSH agent (not started in cron's environment)
   - Most environment variables (PATH, HOME may differ)

   So when `unified_ddp.py` calls `subprocess.run(["git", "push"])`, git tries to authenticate via HTTPS, can't reach Keychain, has no credentials, and fails silently (or with an auth error that the script catches and reports as "push failed").

### Root cause:
**HTTPS git authentication depends on macOS Keychain, which is inaccessible from cron/launchd execution contexts.** The scraper itself (Python + Playwright) doesn't need auth — only the final `git push` step does.

### Why this wasn't caught earlier:
- Manual pushes from Terminal always worked (Keychain available in interactive sessions)
- The scraper was only recently automated via cron (March 11)
- The script correctly reported the failure via Telegram, but no agent existed to act on it

---

## 3. Decision — Fix Options Evaluated

| Option | Approach | Pros | Cons | Verdict |
|--------|----------|------|------|---------|
| **A** | Switch remote to SSH with ed25519 key | No password/token needed. Key file is always accessible. Industry standard for automation. Most secure (private key never transmitted). | Requires one-time SSH key setup on GitHub. | **CHOSEN** |
| **B** | GitHub Personal Access Token (PAT) via credential helper | Simple to set up. | Token is a string that can be stolen. Tokens expire (90 days default). Stored in plaintext by `git credential store`. Less secure. | Rejected |
| **C** | Fix Keychain access in cron environment | Keeps HTTPS. | Complex macOS-specific hacks. Fragile across OS updates. Unreliable. | Rejected |

**Decision rationale:** SSH key authentication is the root cause fix. It works headlessly by design — the private key file sits on disk at `~/.ssh/id_ed25519` with 600 permissions, and git reads it directly without any credential helper or Keychain dependency. This is how every CI/CD system in the world handles automated git operations.

---

## 4. Fix — Step-by-Step Implementation

### Step 4.1: Generate SSH key pair

```bash
ssh-keygen -t ed25519 -C "solosevn@gmail.com" -f ~/.ssh/id_ed25519 -N ""
```

- **Algorithm:** ed25519 (modern, fast, secure — 256-bit equivalent strength)
- **No passphrase** (`-N ""`) — required for headless/cron operation. A passphrase would require interactive input.
- **Output:** Two files:
  - `~/.ssh/id_ed25519` (private key — NEVER share, 600 permissions)
  - `~/.ssh/id_ed25519.pub` (public key — safe to share, goes to GitHub)

### Step 4.2: Set directory permissions

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

SSH refuses to use keys with overly permissive file permissions. This is a security feature.

### Step 4.3: Add GitHub to known_hosts

```bash
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts
```

This prevents the "Are you sure you want to continue connecting?" prompt that would hang a cron job. It stores GitHub's server fingerprint so SSH can verify it's talking to the real GitHub.

### Step 4.4: Add public key to GitHub account

1. Navigate to github.com → Settings → SSH and GPG keys → New SSH key
2. Title: `TR2-Mac-Cron (Gimli DDP automation)` (descriptive — you'll know what this key is for)
3. Key type: Authentication Key
4. Paste contents of `~/.ssh/id_ed25519.pub`
5. Click "Add SSH key" (requires 2FA confirmation)

### Step 4.5: Switch git remote from HTTPS to SSH

```bash
cd ~/Desktop/TR2
git remote set-url origin git@github.com:solosevn/TR2.git
```

**Before:** `https://github.com/solosevn/TR2.git`
**After:** `git@github.com:solosevn/TR2.git`

Same repo, same code, same website. Only the authentication transport changes.

### Step 4.6: Test SSH connection

```bash
ssh -T git@github.com
```

Expected output:
```
Hi solosevn! You've successfully authenticated, but GitHub does not provide shell access.
```

This confirms: key is on disk → SSH reads it → GitHub accepts it → authenticated.

### Step 4.7: Push pending data

```bash
cd ~/Desktop/TR2 && git push
```

This pushed both the morning's scraper data (1337 models) and any pending commits via SSH.

---

## 5. Verification — Proving the Fix Works

1. **SSH test passed:** `Hi solosevn! You've successfully authenticated`
2. **Git push succeeded:** `To github.com:solosevn/TR2.git  51f8c4e..fc8cec9  main -> main`
3. **GitHub commits page:** Shows March 12 commits — "TR2 unified update 2026-03-12 (1337 models)" and "Replace index.html with unified version"
4. **GitHub Pages deployed:** Deployment #33 active, live at solosevn.github.io/TR2/
5. **Live site verified:** Shows "Updated Mar 12 · 5:13 AM CST | 37 sources fired | 1337 models ranked"

**The cron job will now work autonomously every night** because SSH key auth doesn't depend on Keychain, user sessions, or any macOS GUI context.

---

## 6. Side Issue Encountered — Stale Git Lock File

During the fix, an `index.lock` file was left in `.git/` by a concurrent git process (the Cowork VM ran `git status` while the repo was mounted). This blocked the next `git commit` with:

```
fatal: Unable to create '/Users/davidsolomon/Desktop/TR2/.git/index.lock': File exists.
Another git process seems to be running in this repository
```

**Fix:** `rm -f .git/index.lock` — safe to remove when no git operation is actually running. This is a common issue when git crashes mid-operation or when multiple tools access the same repo.

**Lesson for agents:** Before any git operation, check for stale lock files:
```bash
if [ -f .git/index.lock ]; then
    # Check if any git process is actually running
    if ! pgrep -f "git.*$(basename $PWD)" > /dev/null; then
        rm -f .git/index.lock
        echo "Removed stale git lock file"
    fi
fi
```

---

## 7. Pattern — When You'll See This Again

This failure pattern will recur ANY time a new automated script needs to push to GitHub from a non-interactive context:

- **New agent scripts** that commit and push results
- **Cron jobs** for any repo (not just TR2)
- **launchd agents** running as daemons
- **tmux sessions** started at boot (before user login)

**The rule:** If a script runs without a human logged into the GUI, it cannot use HTTPS+Keychain for git. Use SSH keys.

---

## 8. Security Context

| Aspect | Status |
|--------|--------|
| SSH key type | ed25519 (current best practice) |
| Passphrase | None (required for automation) |
| GitHub 2FA | Enabled (Authenticator app) |
| Key scope | Authentication only (read/write to repos) |
| Revocation | Delete key from github.com/settings/keys instantly revokes access |
| Physical security | Private key exists only on David's Mac at ~/.ssh/id_ed25519 |

**If the Mac is compromised:** Delete the SSH key from GitHub settings. Access is instantly revoked. Generate a new key on the replacement machine.

---

## 9. Relevance to TR2 Agents

### For Treebeard (TRSbench Monitor):
When monitoring TRSbench data freshness, check not just "did Gimli run?" but "did the data reach production?" Compare the timestamp in `status.json` (local) against what's live on GitHub. If local is newer than production, the push failed.

### For Sauron (TR Site Manager):
During the 6-8AM audit cycle, one check should verify: "Is the live site data timestamp from today?" If the cron ran at 4AM but the site shows yesterday's date, diagnose the push pipeline (check git remote, SSH key presence, network connectivity).

### For Elrond (TrainingRun COO):
When reviewing Sauron and Treebeard's huddle reports, watch for patterns like "data fresh locally but stale on production." This indicates a delivery pipeline issue, not a scraper issue. The fix is always in the push mechanism, not the scraper.

### For Gandalf (CEO):
If this pattern recurs across multiple agents pushing to different repos, it's a system-wide SSH key management issue. Consider: is the key still valid? Did GitHub revoke it? Is the SSH agent running? Log to The Red Book as infrastructure knowledge.

---

## 10. Commands Quick Reference (for future agents)

```bash
# Check if SSH is working
ssh -T git@github.com

# Check what remote a repo uses
git remote -v

# Switch from HTTPS to SSH
git remote set-url origin git@github.com:USERNAME/REPO.git

# Test a push
git push --dry-run

# Check for stale lock files
ls -la .git/index.lock

# Remove stale lock (only if no git process running)
rm -f .git/index.lock

# Check if SSH key exists
ls -la ~/.ssh/id_ed25519

# Verify key fingerprint matches GitHub
ssh-keygen -lf ~/.ssh/id_ed25519.pub
```

---

*This document is training data for TR2 autonomous agents. It should be loaded into the relevant agent's memory/ directory and referenced during diagnosis of git push failures, deployment pipeline issues, or data freshness problems.*
