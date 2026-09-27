# igt — Instagram/YouTube/Facebook/TikTok transcript CLI

[![CI](https://github.com/metviz/igt/actions/workflows/ci.yml/badge.svg)](https://github.com/metviz/igt/actions/workflows/ci.yml)

Command-line counterpart of the Instagram Transcript Generator Chrome extension (a separate project). Downloads an
Instagram reel/post's, YouTube video's, Facebook reel/video's or TikTok video's audio with
[yt-dlp](https://github.com/yt-dlp/yt-dlp) and transcribes it locally with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). No server needed.

## Install

```bash
cd igt
uv sync
uv run igt --help
```

Without `uv`, use the pinned `requirements.txt` instead (regenerate it with
`uv export --no-hashes --no-dev -o requirements.txt` after changing dependencies):

```bash
cd igt
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
igt --help
```

The first run downloads the Whisper model (`base` by default).

## Usage

```bash
igt https://www.instagram.com/reel/ABC123xyz/                 # transcript text to stdout
igt https://www.youtube.com/watch?v=dQw4w9WgXcQ                # or a YouTube video/short
igt https://www.facebook.com/reel/1234567890123456             # or a Facebook reel/video/fb.watch link
igt https://www.tiktok.com/@someuser/video/7123456789012345678  # or a TikTok video/short link
igt URL --format md                                            # txt | srt | json | md (markdown: source URL, metadata, caption, timestamped transcript)
igt URL --format srt > captions.srt                            # numbered cues with HH:MM:SS,mmm timestamps
igt URL --language hi --model small                            # skip auto-detect, bigger model
igt URL --cookies-from firefox                                 # login-walled videos: use your browser session
igt URL --cookies ~/secrets/instagram-cookies.txt              # ...or an exported cookies file (outside the repo)
IGT_OUT_ROOT=~/transcripts igt URL --out --format srt          # writes ~/transcripts/ABC123xyz.srt
```

Accepted URLs: `instagram.com/(reel|p|tv)/<id>/` (optionally with a `/<username>/` prefix);
`youtube.com/watch?v=<id>`, `youtube.com/shorts/<id>`, `youtu.be/<id>`; `facebook.com/reel/<id>/`,
`facebook.com/(<username>/)videos/<id>/`, `facebook.com/watch/?v=<id>`, `fb.watch/<code>`; or
`tiktok.com/@<username>/video/<id>/`, `vm.tiktok.com/<code>`, `vt.tiktok.com/<code>`. Tracking
parameters such as `?igsh=` or `&t=` are dropped.

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

`--format json` and `--format md` include the video's creator, upload date, duration, caption and hashtags
(taken from yt-dlp; fields the source site doesn't provide are left empty). `--cookies` and `--cookies-from` are
mutually exclusive; `--cookies-from` wins over `IGT_COOKIES_FILE`.

Errors go to stderr as `error: <message>`; stdout carries only the result.

## Development

```bash
uv run pytest --cov=igt                       # unit tests, no network
IGT_TEST_URL=<public reel> uv run pytest -m integration   # opt-in live smoke test
```

CI runs the unit tests on every push/PR (required) plus a live smoke test against a public
Instagram reel (non-blocking: `continue-on-error`, since it depends on Instagram staying reachable
and that specific reel staying up). See `.github/workflows/ci.yml`.

yt-dlp's extractors for these sites break periodically (TikTok's most often); update with
`uv lock --upgrade-package yt-dlp`.

Only download content you have the right to use, and respect each site's Terms of Service.
