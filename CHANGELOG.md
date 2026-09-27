# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/) (`MAJOR.MINOR.PATCH`, 0.x = no stability guarantees yet).

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

[0.1.1]: https://github.com/metviz/igt/releases/tag/v0.1.1
[0.1.0]: https://github.com/metviz/igt/releases/tag/v0.1.0
