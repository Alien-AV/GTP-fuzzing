# Runbook

## Campaign Inputs

Before the first run in a campaign, collect:
- client SSH control IP
- server SSH control IP
- client traffic IP used in the GTP payloads
- server traffic IP used in the GTP payloads

Optional:
- GW management IP and authentication details for crash monitoring

Do not assume the traffic IPs are reachable over SSH or vice versa.

Store these values in the repo-root local config:
- `fuzz-lab.local.json`

This file is intentionally gitignored.

## SSH MCP Verification

Before using this runbook, verify that the Codex app has the `ssh-mcp` MCP configured.

If it is missing, prompt the user to let the agent install it for them and quote the relevant local README instructions from:
- `ssh-mcp/README.md`

The relevant install command in that README is:
```powershell
cd ssh-mcp
py -3 -m pip install --user .
```

## Iteration Discipline

For each fuzz run:
- assign a new iteration id with `scripts/new-iteration.ps1`
- append one local line to `gtp_mts_fuzz_iterations.log`
- create dedicated client and server XML copies for that iteration
- keep the same iteration id on both sides

Suggested helper usage:
```powershell
powershell -File gtp-mts-fuzzing\\scripts\\new-iteration.ps1 -Summary "declared Create Session length shorter than encoded payload"
```

Suggested per-iteration filenames:
- `codex_iter-0001_GTPv2_CreateSessionRequest.xml`
- `codex_iter-0001_GTPv2_CreateSessionResponse.xml`

## Remote Preconditions

- client host: sample `10.10.10.126`
- server host: sample `10.10.10.127`
- MTS path: `~/mts/tutorial/gtp/load/Release13/`
- verify `2123` is free before launch

Expected remote files under `~/mts/tutorial/gtp/load/Release13/`:
- `test.xml`
- `tests.conf.txt`
- `gtp.properties`
- client and server scenario subdirectories

The sample IPs in this document are examples only.

Actual control and traffic IPs must come from the user on first run and be stored in `fuzz-lab.local.json`.

Check:
```bash
ss -lunp | grep ':2123 ' || true
```

Kill stale Release13 runs if needed:
```bash
pkill -f 'Release13/test.xml' || true
```

Prepare per-iteration directories:
```bash
mkdir -p ~/mts/tutorial/gtp/load/Release13/codex_fuzz/client
mkdir -p ~/mts/tutorial/gtp/load/Release13/codex_fuzz/server
```

## Verified Release13 Test 9 Launch

Server:
```bash
cd ~/mts/bin
JAVA_HOME=$(cat java_home)
JAVA_MEMORY=$(cat java_memory)
JAVA_ARGUMENTS=$(cat java_arguments | tr ';' ':')
export LD_LIBRARY_PATH=../lib/native
cmd=("$JAVA_HOME/java" "-Xmx${JAVA_MEMORY}m")
for arg in $JAVA_ARGUMENTS; do cmd+=("$arg"); done
cmd+=(com.devoteam.srit.xmlloader.cmd.TextImplementation ../tutorial/gtp/load/Release13/test.xml "Create Session Response" -param:[localHost]+10.10.10.127 -param:[remoteHost]+10.10.10.126 -storageLog:file -levelLog:DEBUG -genReport:true)
nohup "${cmd[@]}" > /tmp/mts_server_java_nohup.log 2>&1 < /dev/null &
```

Client:
```bash
sleep 2
cd ~/mts/bin
JAVA_HOME=$(cat java_home)
JAVA_MEMORY=$(cat java_memory)
JAVA_ARGUMENTS=$(cat java_arguments | tr ';' ':')
export LD_LIBRARY_PATH=../lib/native
cmd=("$JAVA_HOME/java" "-Xmx${JAVA_MEMORY}m")
for arg in $JAVA_ARGUMENTS; do cmd+=("$arg"); done
cmd+=(com.devoteam.srit.xmlloader.cmd.TextImplementation ../tutorial/gtp/load/Release13/test.xml "Create Session Request" -param:[localHost]+10.10.10.126 -param:[remoteHost]+10.10.10.127 -storageLog:file -levelLog:DEBUG -genReport:true)
nohup "${cmd[@]}" > /tmp/mts_client_java_nohup.log 2>&1 < /dev/null &
```

## Why Direct Java

`startCmd.sh` and `startClass.sh` pass args with unquoted `$*`.

That breaks testcase names with spaces:
- `"Create Session Request"`
- `"Create Session Response"`

Direct Java preserves them.

## GUI Caveat

GUI parameter edits are session-only.

If the user changes hosts or ports through a GUI parameter editor, those changes should not be assumed to persist to disk.

## Proven Baselines

Two baseline executions are known to work in this environment model:
- the tutorial `111_create_session_request` pair
- the original `Release13/test.xml` `Test 9` pair

## CLI Output Rule

Ignore MTS CLI output for test interpretation.

Do not expect meaningful progress, diagnostics, or final status from stdout or the nohup output file.

Use it only for narrow operational checks such as:
- process launched
- port conflict
- obvious startup failure before MTS hands off to its own logs

For actual test outcome, go straight to:
- scenario logs
- `testPlan.csv`
- `application.log`

## Baseline Replay Rule

Replay the known-good baseline:
- every 20 mutation iterations
- after port conflicts
- after killing stale Java/MTS listeners
- after any host or traffic IP changes

If the baseline stops working, stop interpreting subsequent fuzz results until the environment is stable again.

## What To Check After Launch

Server:
```bash
tail -120 ~/mts/logs/'Create Session Response_1'/GTP.V2.log
tail -20 ~/mts/logs/testPlan.csv
```

Client:
```bash
tail -120 ~/mts/logs/'Create Session Request_1'/client.log
tail -20 ~/mts/logs/testPlan.csv
```

Reports:
```bash
find ~/mts/reports -maxdepth 1 -type d -name 'TEST_*' | sort | tail -5
```

## Recommended Mutation Layout

Keep per-iteration copies under a dedicated fuzz area when possible.

Example:
```bash
~/mts/tutorial/gtp/load/Release13/codex_fuzz/client/
~/mts/tutorial/gtp/load/Release13/codex_fuzz/server/
```

If that is not convenient, keep the copied XMLs beside the original samples, but still use unique iteration-specific filenames.
