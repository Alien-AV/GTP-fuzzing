# GTP MTS Fuzzing Skill

This repository contains the `gtp-mts-fuzzing` Codex skill and its references.

## Setup

1. Drop the skill directory into `./.codex/agents` in the target workdir.
2. Make sure `ssh-mcp` is installed and available to the agent.
3. Unpack the local MTS trees as needed into:
   - `mts/`
   - `mts_client/`
   - `mts_server/`

This repo also includes a local copy of [`ssh-mcp`](C:/Code/GTP-fuzzing/ssh-mcp).
Its local install instructions are in [ssh-mcp/README.md](C:/Code/GTP-fuzzing/ssh-mcp/README.md).

## Use

Ask the agent with a prompt such as:

```text
$gtp-mts-fuzzing let's configure the environment
```
