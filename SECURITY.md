# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x | yes |
| < 1.0 | no |

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Use GitHub's private vulnerability reporting:

1. Go to the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Describe the issue, the affected mode/driver, and a minimal reproduction.

If private reporting is unavailable, open a minimal issue that only asks for a
private channel — do not include exploit details.

## Scope

In scope:

- unintended keystrokes or sends to the wrong window
- clipboard leakage beyond the documented behaviour
- CDP connection handling and target selection
- command construction in `opencode.completion_mode = "api"`
- profile parsing that could execute code
- path or regex handling that could target the wrong process

Out of scope:

- the security of ChatGPT, Brave, OpenCode, or Windows themselves
- accounts or content you choose to relay
- running the tool unattended without a time cap
- exposing a CDP debugging port to a network

## Design notes

- LoopBridge makes no outbound network calls of its own. CDP connects to
  `127.0.0.1` only.
- It stores no credentials and has no telemetry.
- The clipboard is used as the transport; treat relayed text as sensitive.
- `--dry-run` focuses windows but does not paste or send. `--simulate` touches
  no real window.

## Disclosure

Please give a reasonable window to fix the issue before public disclosure.
Credit will be given unless you ask otherwise.
