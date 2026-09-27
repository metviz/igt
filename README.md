# igt — Instagram transcript CLI

Command-line counterpart of the Instagram Transcript Generator Chrome extension (a separate project). Downloads a reel/post's audio with
[yt-dlp](https://github.com/yt-dlp/yt-dlp) and transcribes it locally with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). No server needed.

## Install

```bash
cd igt
uv sync
uv run igt --help
```

The first run downloads the Whisper model (`base` by default).

## Usage

```bash
igt https://www.instagram.com/reel/ABC123xyz/                 # transcript text to stdout
igt URL --format srt                                           # txt | srt | json
igt URL --language hi --model small                            # skip auto-detect, bigger model
igt URL --cookies ~/secrets/instagram-cookies.txt              # login-walled posts
IGT_OUT_ROOT=~/transcripts igt URL --out --format srt          # writes ~/transcripts/ABC123xyz.srt
```

Accepted URLs: `instagram.com/(reel|p|tv)/<id>/`, optionally with a `/<username>/` prefix. Tracking
parameters such as `?igsh=` are dropped.

## Environment

| Variable | Meaning |
|---|---|
| `IGT_OUT_ROOT` | Directory for `--out`. **Required** with `--out`; must be outside this repository. |
| `IGT_COOKIES_FILE` | Netscape-format cookies file (same as `--cookies`). Must be outside this repository. |

There are no path defaults inside the repo: an unset `IGT_OUT_ROOT` is an error, not a fallback.
Cookies are credentials — keep the file out of the repo.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Transcript produced |
| 2 | Bad URL or usage |
| 3 | Configuration error (missing/forbidden path) |
| 4 | Download failed (login required, no video, rate limit, ...) |
| 5 | Transcription failed, or no speech detected |
| 130 | Interrupted (Ctrl-C) |

Errors go to stderr as `error: <message>`; stdout carries only the result.

## Development

```bash
uv run pytest --cov=igt                       # unit tests, no network
IGT_TEST_URL=<public reel> uv run pytest -m integration   # opt-in live smoke test
```

yt-dlp's Instagram extractor breaks periodically; update with `uv lock --upgrade-package yt-dlp`.

Only download content you have the right to use, and respect Instagram's Terms of Service.
