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
  to `md` ("On-screen text" section) and `json` (`on_screen`). Engines via `--ocr-engine`: `rapidocr`
  (default; optional extra: `pip install 'igt[rapidocr]'`) or `tesseract` (system binary).
  `--ocr-merge {fuzzy,exact,off}` controls how repeated text is collapsed (default `fuzzy`).
  A silent video with readable on-screen text no longer fails with "no speech".
- `--format idea` writes a project-idea brief (requirements checklist, open questions, brainstorm prompts
  embedding the extracted content). Template-based; no LLM call. `--out` saves it as `<shortcode>.md`.
- `--idea-llm` (with `--format idea`) adds an LLM-written analysis via Anthropic (`--llm-model`; optional
  extra `igt[llm]`; key from `ANTHROPIC_API_KEY`). Sends the extracted text to Anthropic. Exit 6 on API failure.
- `--llm-provider ollama` runs `--idea-llm` on a local Ollama model (`OLLAMA_HOST`, default `llama3.1:8b`; stdlib
  only, no extra dependency). `--llm-model` overrides the default for either provider.

### Fixed
- Facebook share links (`facebook.com/share/r/<code>`, `/share/v/<code>`) are accepted.
- `--format idea` heading is now short: a social-media caption used as the title loses its "N reactions |"
  prefix and "| Author" suffix, is cut to the first sentence, and is capped at 100 characters.

### Changed
- Open questions are grouped into core functionality, technical stack, scale and security, and scope and
  phasing; the requirements checklist gains a Given/When/Then acceptance-criteria item.
- `--idea-llm` prompt asks the model to tie requirements to the material, tag unsupported items
  `[ASSUMPTION]`, avoid vague phrasing, add acceptance criteria, and write a "Follow-up questions" section.
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
