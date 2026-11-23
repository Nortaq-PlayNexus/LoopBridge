# Pull request

## What changed

<!-- One or two sentences. Link the issue if there is one. -->

## Why

<!-- The problem this solves. -->

## How tested

- [ ] `python tests/test_loop.py`
- [ ] `$env:QT_QPA_PLATFORM="offscreen"; python tests/smoke_gui.py`
- [ ] manual run in `--simulate`
- [ ] manual run in `--dry-run`
- [ ] manual real run (describe the windows/drivers)

## Checklist

- [ ] No secrets, tokens, or private conversation text
- [ ] New config fields documented in `docs/configuration.md`
- [ ] README limitations still accurate
- [ ] Screenshots updated if the UI changed
- [ ] Typed errors used instead of generic exceptions
- [ ] No new network calls or telemetry

## Notes for reviewers

<!-- Anything fragile, platform-specific, or worth re-testing after a UI update. -->
