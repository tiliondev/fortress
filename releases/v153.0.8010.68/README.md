# Fortress 153.0.8010.68

**Release candidate record.** The archives below are built and validated; publication follows maintainer review. This directory records their identities and does not contain the binary archives.

## Downloads

| Platform | Archive | Bytes |
| --- | --- | ---: |
| Linux x64 | `fortress-v153-linux-x64.tar.gz` | 274,436,641 |
| Windows x64 | `fortress-v153-win-x64.zip` | 219,358,333 |

macOS will be added separately. Keep the complete runtime bundle together.

## Licensing

Both builds use the production `k1` keyring and verify signed licenses offline in the native engine. A valid key enables v3; a missing or invalid key leaves the browser in v1 mode with one notice. The internal license bypass is disabled.

The activation client is the same file shipped in the prior public Linux release. It saves the key to `~/.tilion/license.jwt`; `TILION_LICENSE_KEY` takes precedence. Personal license keys are not included in the archives.

The Windows bundle provides `tilion.cmd` for activation and license commands and retains `tillion.cmd` as the native launcher. The activation command requires Python 3. The Linux bundle includes `tilion-activate` and the same standard-library client.

```sh
# Linux, after extracting the published archive
./fortress-v153/tilion activate
./fortress-v153/tilion license status --json
```

```bat
REM Windows, after extracting the published archive
fortress-v153-win-x64\tilion.cmd activate
fortress-v153-win-x64\tilion.cmd license status --json
```

## Verification

[`manifest.json`](manifest.json) binds each archive to its native engine digest. On Windows the engine identity is the hash of `chrome.dll`; checking only `chrome.exe` does not identify the build.

[`VALIDATION.json`](VALIDATION.json) records the native license tests, packaged-launcher checks, and their limits. Linux also passed canvas, audio, receiver, and WebGL smoke checks. These are runtime correctness checks, not an assertion that every website accepts the browser.

The version is based on Chromium revision `95854674670e4bf7c73482b38f8f27b6602165a0` and engine source base `9ec97cade0c8bcf6e81f1285fa5709c2e8871536`, with public license enforcement restored. The public demonstration patch set is described in [`patches/README.md`](../../patches/README.md); it is not the complete binary source input.

Before publication, validate this record against the retained archives:

```sh
python tools/verify_release.py v153.0.8010.68 \
  --manifest releases/v153.0.8010.68/manifest.json \
  --artifacts-dir /path/to/artifacts
```

The artifact directory may contain the archives directly or under `linux-x64/` and `win-x64/`. After publication, the same verifier can check the release's uploaded assets:

```sh
python tools/verify_release.py v153.0.8010.68 --full
```

Publication of this version does not move the existing latest-release selection or the SDK channel defaults automatically. Those are separate release decisions.
