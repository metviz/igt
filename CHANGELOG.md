# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/) (`MAJOR.MINOR.PATCH`, 0.x = no stability guarantees yet).

## [Unreleased]

### Added
- `--out-file PATH` writes the result to `PATH` (relative to the output directory, or absolute).
  Mutually exclusive with `--out`.
- `--mp3` saves the audio as `<shortcode>.mp3` (or `--out-file PATH`) instead of transcribing.
  Requires `ffmpeg`; `--format` is ignored.
- `--ocr` reads on-screen text from sampled video frames (`--ocr-every SECONDS`, default 2) and adds it
  to `md` ("On-screen text" section) and `json` (`on_screen`). Engines via `--ocr-engine`: `tesseract`
  (default, system binary) or `rapidocr` (optional extra: `pip install 'igt[rapidocr]'`).
  A silent video with readable on-screen text no longer fails with "no speech".

### Changed
- The output directory for `--out` and relative `--out-file` is `$IGT_OUT_ROOT` if set, otherwise the
  current directory. Previously an unset `IGT_OUT_ROOT` was a configuration error (exit 3). A directory
  inside the repository is still rejected.
- Output paths that are existing directories are now refused before any download.

### Removed
- Unused `litellm` dependency.

## [0.1.1] - 2026-09-27

### Added
- Disclaimer section: no platform affiliation, user responsible for ToS/copyright compliance,
  MIT/"as is" pointer.
- `ffmpeg` documented as a required prerequisite.
- CI: macOS added to the unit-test matrix alongside Ubuntu.

## [0.1.0] - 2026-09-27

Initial public release.

### Added
- `igt <url>` downloads a video's audio with yt-dlp and transcribes it locally with faster-whisper.
- URL support: Instagram (reel/post/tv), YouTube (watch/shorts), Facebook (reel/videos/watch/fb.watch),
  TikTok (video, vm/vt.tiktok.com short links).
- Output formats: `txt`, `srt`, `json`, `md`. `--out` writes to `$IGT_OUT_ROOT` instead of stdout.
- Post metadata: creator, upload date, duration, caption, hashtags.
- `--cookies` / `--cookies-from BROWSER` for login-walled videos.
- `--language` and `--model` to control transcription.
- Strict host allow-list and path validation for every accepted URL; output path validated
  (dir creatable/writable, not a symlink) before any download.
- MIT license.
- GitHub Actions CI: unit suite (required) plus a non-blocking live smoke test.

[Unreleased]: https://github.com/metviz/igt/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/metviz/igt/releases/tag/v0.1.1
[0.1.0]: https://github.com/metviz/igt/releases/tag/v0.1.0
