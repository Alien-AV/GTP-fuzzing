# Artifact Guide

## Trustworthy Artifacts

### 1. Scenario log

Server:
- `~/mts/logs/Create Session Response_1/GTP.V2.log`

Client:
- `~/mts/logs/Create Session Request_1/client.log`

Use these to confirm:
- actual send/receive operations
- decoded GTP messages
- extracted header and IE values
- scenario completion
- which per-iteration XML actually ran, if the testcase or log naming was customized

Successful signals include:
- `SEND>>>`
- `<receiveMessageGTP> OK`
- `ScenarioRunner OK`
- client-side decode of `Create Session Response:33`

### 2. Test plan CSV

- `~/mts/logs/testPlan.csv`

Use this for quick pass/fail summary by testcase.

### 3. Application log

- `~/mts/logs/application.log`

Use this for:
- report generation
- top-level lifecycle
- general logging context

## Logging Controls

Useful MTS logging/report flags for CLI work:
- `-storageLog:file`
- `-levelLog:DEBUG`
- `-genReport:true`

Why they matter:
- default property-driven log storage is often not useful for CLI-only interpretation
- forcing file-backed logs makes scenario evidence persist on disk

## Potentially Misleading Artifacts

### CLI stdout and nohup output

Treat MTS stdout and nohup output as low-value.

Do not use them to decide whether a fuzz iteration succeeded, failed, or was interesting.

Why:
- the CLI UX is poor
- the startup parameter dump is misleading
- useful execution evidence is usually absent there
- successful runs can still print unresolved-looking placeholders

### HTML reports

HTML pages under `~/mts/reports/TEST_*` can show `KO` even when the scenario log shows a successful exchange.

These pages are still useful for:
- seeing which operation categories were exercised
- browsing parameter value pages
- locating operation-specific report pages

But do not use them as the sole source of truth.

## Useful HTML Files

Examples inside a `TEST_*` directory:
- `_report.html`
- `testcase_Create Session Request.html`
- `testcase_Create Session Response.html`
- `operation_sendMessageGTP.html`
- `operation_receiveMessageGTP.html`
- `operationparameter_file.readproperty.html`
- `parameter_value.html`
- `parametervalue_<name>.html`

What they can tell you:
- testcase and operation timing
- which operation classes ran
- what parameter values MTS recorded in its report layer

What they may get wrong for this workflow:
- final `OK` vs `KO` interpretation
- placeholder-looking parameter values

## Local Campaign Ledger

- `gtp_mts_fuzz_iterations.log`

Use this as the top-level local ledger for the fuzz campaign.

Each line should let you answer:
- when the attempt happened
- which iteration id was used
- what mutation was attempted

This ledger is the index that ties together:
- local mutation intent
- remote per-iteration XML filenames
- remote MTS logs
- any GW crash evidence
