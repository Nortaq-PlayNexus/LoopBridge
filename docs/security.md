# Security

LoopBridge is a local automation tool. It has no server, no telemetry, and no
API keys. Its security surface is the clipboard, synthetic keyboard input, and
the optional Chrome DevTools Protocol connection.

## Threat model

| Surface | Risk | Mitigation |
|---|---|---|
| **Clipboard** | Relayed text (which may contain code or secrets) passes through the Windows clipboard | Run only on a machine you control; clear the clipboard when done; avoid relaying secrets |
| **Synthetic keystrokes** | The tool sends keys to whichever window has focus | Window titles are matched before focus; keep the target windows visible and do not use the machine while a real run is active |
| **CDP port** | `--remote-debugging-port=9222` exposes page control to local processes | Bind only on localhost, close Brave when done, never expose the port to a network |
| **OpenCode CLI mode** | Runs a shell command with the relayed prompt | The command comes from your profile; keep it fixed and review it |
| **Profile JSON** | Contains window regexes and commands, not credentials | Do not put tokens or passwords in it |
| **Unattended loop** | Two models can exchange text indefinitely | Use `--count`, `watchdog.max_run_time_s`, and the Stop control |

## What LoopBridge does not do

- It does not call OpenAI, Anthropic, or any model API.
- It does not store, upload, or log to a remote service.
- It does not read files or environment variables for secrets.
- It does not install a service, driver, or startup entry.
- It does not bypass authentication or rate limits.

## Recommendations

1. Run with `--simulate` first, then `--dry-run`, then a short real run.
2. Keep `watchdog.max_run_time_s` set for unattended use.
3. Use CDP mode only locally and close the debugging port afterwards.
4. Review what the loop is about to send before leaving it unattended.
5. Do not relay credentials, personal data, or anything you would not paste
   into both applications manually.
6. Respect the terms of service of every application being automated.

## Reporting a vulnerability

Please do not open a public issue for a security problem. See
[`SECURITY.md`](../SECURITY.md) for the private reporting process.
