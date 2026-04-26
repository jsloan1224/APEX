# BOOTSTRAP_TEMPLATE.md

**Purpose:** This is a reference for what to put in your Claude project's bootstrap file (the file that gets attached to every conversation in the project). When you start a new chat, Claude reads the bootstrap as its first user message.

**How to use:** Copy the block below and paste it into your project's bootstrap file in claude.ai (Project Settings → Edit Bootstrap, or wherever the bootstrap field is).

Replace the placeholder PAT with a fresh one from your jsloan1224 GitHub account (Settings → Developer Settings → Fine-grained tokens → Contents read/write on the APEX repo). Generate a new PAT every session for security.

---

## Bootstrap text to paste

```
APEX project bootstrap.

Repo: https://github.com/jsloan1224/APEX
Working branch: build  (never push to main)

Clone with this PAT:
<YOUR_GITHUB_PAT_HERE>

After cloning, check out the build branch:
  git checkout build

Then read these files in order before doing anything else:
1. SESSION_HANDOFF.md  (entry point — points to the rest)
2. CLAUDE.md           (rules of engagement)
3. PROJECT_STATE.md    (what's built, what's next)
4. BACKLOG.md          (open issues and deferred decisions)

Then give me a one-paragraph status report:
- What phase is complete
- What phase is next
- Any open questions from BACKLOG that need my input before proceeding

Do not propose work, write code, run audits, or read source files until the
status report is delivered and I respond. Phase audits are end-of-session,
not start-of-session.
```

---

## Why this works

- **Forces Claude to read the handoff docs first.** Without this, Claude will start improvising on whatever I say in the first message.
- **`SESSION_HANDOFF.md` is the entry point** — it points to the other three docs in the right order.
- **One-paragraph status report at the start.** Confirms Claude actually read the docs before responding to whatever I want to do next.
- **PAT is regenerated each session** — limits exposure if a token is captured in chat logs or screenshots.

## When to update this file

Update `BOOTSTRAP_TEMPLATE.md` (this file) whenever:
- A new top-level doc is added to the repo (add it to the read list)
- A doc is renamed or moved
- The repo URL changes
- The handoff process changes substantively

Update the actual bootstrap field in claude.ai whenever this file changes.
