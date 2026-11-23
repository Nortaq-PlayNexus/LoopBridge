# Deployment

LoopBridge is a local Windows desktop tool. "Deployment" means running it from
source or shipping a standalone executable.

## Run from source

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

For a GUI shortcut, create a shortcut to:

```powershell
.venv\Scripts\python.exe run.py --gui
```

Set the working directory to the repository root so
`loopbridge-profile.json` is found.

## Build a standalone executable

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name LoopBridge --onefile ^
  --collect-submodules loopbridge run.py
```

Output: `dist/LoopBridge.exe`.

Notes:

- `--windowed` hides the console. Use the console build if you want to watch
  logs while the loop runs.
- `--collect-submodules loopbridge` is required so the driver modules are
  bundled.
- The exe still needs the same external apps: Brave with ChatGPT, and a terminal
  running OpenCode.
- Windows SmartScreen may warn on an unsigned exe. That is expected for a local
  build.

## Releases

The repository ships a GitHub Actions workflow that builds the exe on a `v*` tag
and attaches it to the release:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

The workflow is [`.github/workflows/release.yml`](../.github/workflows/release.yml).

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on
`windows-latest` for Python 3.10, 3.11, and 3.12:

- installs `requirements.txt`
- runs `python tests/test_loop.py`
- runs the headless GUI smoke test with `QT_QPA_PLATFORM=offscreen`
- byte-compiles the package

## Uninstall

Delete the repository folder or the extracted exe. LoopBridge writes no
registry keys, installs no service, and stores no data outside the profile JSON
you choose. It does use the Windows clipboard while running.

## Packaging checklist

- [ ] `python tests/test_loop.py` passes
- [ ] headless GUI smoke test passes
- [ ] version bumped in `pyproject.toml` and `CHANGELOG.md`
- [ ] release notes describe driver/config changes
- [ ] `README.md` limitations still accurate
