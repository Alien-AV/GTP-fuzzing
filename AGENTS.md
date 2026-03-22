# Task Notes

## Objective

Verify the remote MTS GTP `Release13` layouts on:
- client host provided by the user
- server host provided by the user

Then run a basic Create Session server-listen -> client-send flow and understand how to execute and debug it reliably.

The concrete IPs used during the original investigation were environment-specific examples and should not be treated as defaults for future runs.

Actual control IPs, traffic IPs, and any optional GW authentication details should be collected from the user on first run and stored in the repo-root local config file `fuzz-lab.local.json`, which is gitignored.

## Remote Layout

Verified on both hosts under `~/mts/tutorial/gtp/load/Release13/`:
- `test.xml`
- `tests.conf.txt`
- `gtp.properties`
- client/server scenario subdirectories

## What Actually Works

Two things are now proven:

1. Cross-host GTP Create Session works in this environment.
- The stripped tutorial `111_create_session_request` pair ran successfully across the two hosts.

2. The original `Release13/test.xml` also works for `Test 9` when run the right way.
- The successful method is to invoke `com.devoteam.srit.xmlloader.cmd.TextImplementation` directly.
- Do not rely on `startCmd.sh` or `startClass.sh` when selecting a testcase by name with spaces. Both wrappers forward args with unquoted `$*`, so `"Create Session Request"` gets broken apart.

## Correct Run Pattern

Important: start the server first, then wait a bit before starting the client.
- The server does not come up instantly.
- Future runs should include a short delay after server launch before client launch.
- A `sleep 2` was enough in our successful runs.

Working direct-Java pattern:

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

## Important Observations

### 1. The startup parameter printout is misleading

At startup MTS prints many unresolved placeholders such as:
- `[localPort]`
- `[v2SequenceNumber]`
- `[v2IMSI]`

That does not necessarily mean the run is broken.

In successful runs:
- the startup banner still showed unresolved placeholders
- but the actual scenario logs showed a valid Create Session exchange
- both sides completed normally

### 2. Defaults come from Release13 files

Stock sample addresses are baked into the Release13 XML/property files:
- client local host default: `1.1.1.4`
- client remote host default: `1.1.2.4`
- server local host default: `1.1.2.4`
- server remote host default: `[localHost]` -> `1.1.2.4`

These come from the top-level `test.xml` files, not from hidden runtime state.
They are packaged sample defaults, not the addresses that should be used in a new environment.

### 3. GUI and CLI differ

The GUI "Edit parameters" changes are session-only and do not persist to disk.

CLI equivalent for editable params is:
- `-param:[name]+value`

But the wrapper scripts are not safe for testcase names with spaces. Direct Java invocation is required for named testcase selection.

### 4. SSH MCP cannot safely drive the interactive prompt

Trying to drive the prompt
- `Available commands: (S)top, (K)ill, (R)eport (ENTER to validate):`

through the SSH MCP failed because the tool appends its own completion-marker text, which MTS consumes as bogus commands.

So interactive prompt-driven runs should be done manually by a human, not through this MCP.

## Logs And Reports: What They Are Good For

### Most useful artifacts

1. `~/mts/logs/testPlan.csv`
- quickest pass/fail summary
- good for checking whether the intended testcase recorded `OK`

2. Scenario logs under `~/mts/logs/<testcase>_1/`
- most trustworthy source for actual message exchange
- examples:
  - server: `~/mts/logs/Create Session Response_1/GTP.V2.log`
  - client: `~/mts/logs/Create Session Request_1/client.log`
- these logs contain:
  - receive/send operation results
  - decoded message contents
  - extracted parameter values
  - scenario completion status

3. `~/mts/logs/application.log`
- useful for global execution events
- report generation
- high-level lifecycle messages

4. `~/mts/reports/TEST_*`
- HTML report tree generated by `-genReport:true`
- contains:
  - `_report.html`
  - testcase pages
  - operation pages
  - per-parameter value pages

### Caveat about HTML reports

The HTML reports are not fully trustworthy for this Release13 case.

Observed behavior:
- scenario log showed success
- `testPlan.csv` showed success on the server-side successful run
- but HTML testcase/report pages still showed `KO`
- parameter pages also preserved placeholder-looking values such as `[localPort]`

So:
- trust scenario logs first
- use `testPlan.csv` second
- treat HTML summary pages as supplementary, not authoritative

## Useful Signals Found In Successful Logs

From the successful Release13 run:
- server scenario log showed `SEND>>>` of `Create Session Response:33`
- client scenario log showed `<receiveMessageGTP> OK`
- client scenario log decoded the received `Create Session Response:33`
- scenario logs ended with `ScenarioRunner OK`

That is stronger evidence than the HTML `KO` summary.

## MTS Logging/Report Controls

From `mts/conf/tester.properties` and docs:
- default logs level is `DEBUG`
- default log storage is `MEMORY`
- default report directory is `../reports/`
- default log directory is `../logs/`
- stats automatic generation is disabled by default

Useful CLI flags:
- `-storageLog:file`
- `-levelLog:DEBUG`
- `-genReport:true`

These were necessary to get useful on-disk artifacts from CLI runs.

## Current Understanding

- Remote Release13 trees are present and valid.
- Port `2123` must be free before runs.
- Start server first, then wait briefly, then start client.
- The original `Release13/test.xml` `Test 9` pair works across the two hosts.
- The reliable automated method is direct `TextImplementation` plus named testcase selection plus file logging.
- Wrapper scripts are unsafe for testcase names with spaces.
- Interactive prompt control cannot be automated reliably through the SSH MCP.
- Scenario logs are the main source of truth; HTML summaries can be misleading.
