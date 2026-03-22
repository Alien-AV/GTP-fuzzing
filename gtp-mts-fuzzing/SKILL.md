---
name: gtp-mts-fuzzing
description: Use when working on MTS-based GTP Release13 testing or fuzzing across the remote client/server lab. Covers remote verification, reliable Create Session execution, log/report inspection, and safe iteration on malformed or boundary-value GTP payloads using the available SSH MCP sessions.
---

# GTP MTS Fuzzing

Use this skill for the MTS GTP lab in this workspace.

## Local Setup

This repo does not store the unpacked MTS payload trees.

Before using the skill or running tests, unpack the relevant files into these local directories:
- `mts/`
- `mts_client/`
- `mts_server/`

Expected contents:
- `mts/` contains the base MTS installation, including `bin/`, `conf/`, `doc/`, and tutorial material.
- `mts_client/` contains the client-side GTP scenarios.
- `mts_server/` contains the server-side GTP scenarios.

These directories are intentionally gitignored so the repository stays small.

Store environment-specific connection data in:
- `fuzz-lab.local.json`

This file should live at the repo root and is intentionally gitignored.

Use it for:
- client SSH/control IP
- server SSH/control IP
- client traffic IP
- server traffic IP
- optional GW management IP
- optional GW authentication details

## SSH MCP Requirement

This workflow expects the `ssh-mcp` server to be installed and configured in the Codex app.

Before first use, verify that the SSH MCP is available.

If it is not available, tell the user that this skill requires the local `ssh-mcp` project in this repo:
- `ssh-mcp/`

Installation source:
- `ssh-mcp/README.md`

Local install from this repo:
```powershell
cd ssh-mcp
py -3 -m pip install --user .
```

Codex app MCP setup from this repo:
- Name: `ssh-mcp`
- Transport: `STDIO`
- Command: `py`
- Arguments: `-3`, `-m`, `ssh_mcp.server`
- Working directory: the local `ssh-mcp` folder

If the MCP is missing, provide those instructions before attempting any remote execution.

Local reference trees:
- `mts/`
- `mts_client/`
- `mts_server/`

Primary remote path:
- `~/mts/tutorial/gtp/load/Release13/`

Expected remote `Release13` contents:
- `test.xml`
- `tests.conf.txt`
- `gtp.properties`
- client and server scenario subdirectories

## First-Run Inputs

Before the first remote action in a campaign, ask for:
- client control IP for SSH
- server control IP for SSH
- client-side traffic IP used in the GTP scenarios
- server-side traffic IP used in the GTP scenarios

After collecting them, store them in `fuzz-lab.local.json` and reuse that local config on later runs.

If the user also provides GW access details:
- GW management IP
- GW authentication details

then the skill may also set up crash monitoring for:
- `/var/log/crash`
- `/var/log/dump`
- `/var/log/dump/usermode`

Do not assume the SSH control IPs are the same as the traffic IPs.

## Campaign Log

Every attempted mutation must be logged locally in:
- `gtp_mts_fuzz_iterations.log`

Location:
- workspace root

Format:
- one line per attempt
- prepend an ISO-8601 timestamp
- include a short iteration id
- include a one-line summary of the modification attempted

Example:
- `2026-03-21T14:05:12-04:00 iter-0007 missing RAT Type IE in Create Session Request`

Append this line before launching the remote run so failed launches are still recorded.

Use the helper:
- `scripts/new-iteration.ps1`

This script:
- allocates the next `iter-XXXX`
- appends the ledger line
- prints the paired client/server filenames to use for this run

## Per-Test File Isolation

Do not mutate the shared sample XMLs in place.

For each fuzz iteration:
- copy the original client XML into a dedicated per-iteration filename
- copy the original server XML into a dedicated per-iteration filename
- keep the client and server files paired by the same iteration id
- place them under the remote `codex_fuzz` area when possible

Preferred naming:
- client: `codex_iter-XXXX_<base>.xml`
- server: `codex_iter-XXXX_<base>.xml`

It is fine to create many copies. Cross-reference is more important than keeping the tree minimal.

## What Works

Two baseline facts are proven:
- the stripped tutorial `111_create_session_request` pair worked cross-host
- the original `Release13/test.xml` `Test 9` pair also worked when run the right way

For `Release13` Test 9, the reliable execution path is:
- start server first
- wait briefly before starting client
- use direct `com.devoteam.srit.xmlloader.cmd.TextImplementation`
- preserve testcase names with spaces
- launch through `nohup`
- enable file logs and report generation

Do not rely on `startCmd.sh` or `startClass.sh` for testcase names with spaces. Those wrappers forward args with unquoted `$*`.

Use a delay after server launch.
- `sleep 2` was sufficient in successful runs

The successful automated method is:
- direct `TextImplementation`
- named testcase selection
- `nohup`
- `-storageLog:file -levelLog:DEBUG -genReport:true`

## Canonical Commands

Read [runbook.md](references/runbook.md) before running or modifying tests. It contains:
- verified server/client commands
- nohup form
- direct Java form
- cleanup checks
- where to find results
- remote `codex_fuzz` layout

## Trust Order For Evidence

Use these artifacts in this order:

1. Scenario logs in `~/mts/logs/<testcase>_1/`
2. `~/mts/logs/testPlan.csv`
3. `~/mts/logs/application.log`
4. HTML reports under `~/mts/reports/TEST_*`

Important:
- HTML report pages can show `KO` even when the scenario log clearly shows a successful exchange.
- The startup parameter dump can still show placeholders like `[localPort]` during successful runs.

Strong success signals include:
- `SEND>>>`
- `<receiveMessageGTP> OK`
- `Create Session Response:33` decoded on the client side
- `ScenarioRunner OK`

## CLI Output Rule

Do not expect useful status or diagnostics from the CLI output of MTS commands.

Treat MTS stdout and nohup log output as low-value and generally ignore them for test interpretation.

Reasons:
- the CLI UX is poor
- the startup dump is misleading
- successful runs can still print unresolved-looking placeholders
- pass/fail understanding comes from scenario logs and `testPlan.csv`, not from CLI chatter

Use CLI output only for narrow process-level checks such as:
- confirming the process started
- seeing whether the port is already in use
- locating the generated nohup file

## Default Release13 Addressing

Stock Release13 sample defaults are baked into the vendor files:
- client local host: `1.1.1.4`
- client remote host: `1.1.2.4`
- server local host: `1.1.2.4`
- server remote host defaults to `[localHost]`

Treat those as sample values from the packaged scenarios, not as environment configuration.

Actual run addresses must come from the user on first run and be stored in `fuzz-lab.local.json`.

Override only what is needed:
- `-param:[localHost]+...`
- `-param:[remoteHost]+...`

## Debugging Guidance

When a run looks silent:
- ignore the CLI output unless you are checking process startup
- check `~/mts/logs/testPlan.csv`
- open the scenario log
- confirm `SEND>>>`, `<receiveMessageGTP> OK`, and `ScenarioRunner OK`

If the port is in use:
- inspect `ss -lunp | grep ':2123 '`
- stop stale MTS Java processes before rerunning

If you need more detail:
- include `-storageLog:file -levelLog:DEBUG -genReport:true`

MTS defaults worth remembering:
- default logs level is `DEBUG`
- default log storage in `tester.properties` is `MEMORY`
- report generation is more useful when forced on with `-genReport:true`
- CLI runs are much easier to interpret when `-storageLog:file` is set

GUI caveat:
- GUI parameter edits are session-only and should not be treated as persisted configuration

## Fuzzing Workflow

When moving from baseline execution to parser-focused fuzzing:
- ask for the control and traffic IPs if they have not been supplied yet
- first prove the unmodified Create Session pair still runs
- create a new iteration id with `scripts/new-iteration.ps1`
- append the planned mutation to `gtp_mts_fuzz_iterations.log`
- clone the specific client/server XMLs before editing
- change one protocol dimension at a time
- prefer malformed/boundary-value variations in:
  - header length and sequence values
  - IMSI
  - F-TEID fields
  - Bearer Context
  - AMBR
  - PAA
- keep a known-good baseline command and logs for comparison
- replay the baseline every 20 mutation iterations, and also after any host, port, or listener disturbance
- compare scenario logs and decoded message output after each mutation

When creating malformed payloads, prioritize parser stress over semantic realism.

After each run:
- record the exact iteration id used on both client and server
- capture which per-iteration XML files were executed
- inform the user immediately if GW crash evidence appears

## GW Crash Monitoring

If GW access is available, the skill may use:
- a sub-agent, or
- an automation

to poll the GW every 5 to 10 minutes for new files in:
- `/var/log/crash`
- `/var/log/dump`
- `/var/log/dump/usermode`

Expected behavior:
- capture a baseline listing first
- on each poll, compare against the baseline or prior poll
- if new files appear, alert the user immediately with the path and timestamp

Prefer automation for long-running monitoring. Prefer a sub-agent for short active investigations.

## SSH MCP Notes

Use the SSH MCP for remote execution.

Launch MTS with `nohup`.

Do not try to automate MTS interactive prompts through the SSH MCP:
- `ssh_session_send` appends marker text
- MTS consumes that as bogus prompt input
- ignore the interactive path and use `nohup`

## References

Load these when needed:
- [runbook.md](references/runbook.md)
- [artifact-guide.md](references/artifact-guide.md)
- [fuzzing-targets.md](references/fuzzing-targets.md)
