# igt — Instagram/YouTube/Facebook/TikTok transcript CLI

[![CI](https://github.com/metviz/igt/actions/workflows/ci.yml/badge.svg)](https://github.com/metviz/igt/actions/workflows/ci.yml)

Command-line counterpart of the Instagram Transcript Generator Chrome extension (a separate project). Downloads an
Instagram reel/post's, YouTube video's, Facebook reel/video's or TikTok video's audio with
[yt-dlp](https://github.com/yt-dlp/yt-dlp) and transcribes it locally with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). No server needed.

Beyond the transcript it can save the audio as mp3 (`--mp3`), read on-screen text from the video (`--ocr`),
and turn what it extracted into a project-idea brief with requirements and brainstorm prompts
(`--format idea`, optionally analysed by a local or cloud LLM with `--idea-llm`).

## Install

Requires [`ffmpeg`](https://ffmpeg.org/) on `PATH` (yt-dlp shells out to it for some audio
extraction paths). Preinstalled on GitHub-hosted CI runners; elsewhere: `brew install ffmpeg`
(macOS), `apt install ffmpeg` (Debian/Ubuntu).

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

Optional extras: `pip install 'igt[rapidocr]'` (default OCR engine for `--ocr`) and `pip install 'igt[llm]'`
(Anthropic SDK for `--idea-llm --llm-provider anthropic`; the Ollama provider needs no extra). With uv:
`uv sync --extra rapidocr --extra llm`.

## Usage

```bash
igt https://www.instagram.com/reel/ABC123xyz/                 # transcript text to stdout
igt https://www.youtube.com/watch?v=dQw4w9WgXcQ                # or a YouTube video/short
igt https://www.facebook.com/reel/1234567890123456             # or a Facebook reel/video/fb.watch link
igt https://www.tiktok.com/@someuser/video/7123456789012345678  # or a TikTok video/short link
igt URL --format md                                            # txt | srt | json | md | idea (md: source URL, metadata, caption, timestamped transcript)
igt URL --format srt > captions.srt                            # numbered cues with HH:MM:SS,mmm timestamps
igt URL --language hi --model small                            # skip auto-detect, bigger model
igt URL --cookies-from firefox                                 # login-walled videos: use your browser session
igt URL --cookies ~/secrets/instagram-cookies.txt              # ...or an exported cookies file (outside the repo)
igt URL --out --format srt                                    # writes ./ABC123xyz.srt (see Saving output)
igt URL --out-file notes.md --format md                        # writes ./notes.md
igt URL --mp3                                                  # audio only: writes ./ABC123xyz.mp3, no transcription
igt URL --format idea --out                                    # project-idea brief: requirements stubs + brainstorm prompts (see below)
igt URL --ocr --format md                                      # also read on-screen text (see On-screen text)
igt URL --format idea --idea-llm --llm-provider ollama         # add an LLM analysis, run locally (see Project-idea brief)
```

## On-screen text (OCR)

`--ocr` downloads the video (up to 720p), samples a frame every `--ocr-every SECONDS` (default 2),
and reads each frame with an OCR engine. Repeated on-screen text is merged (`--ocr-merge fuzzy`, the default, tolerates OCR jitter and keeps the fullest version of text being revealed; `exact` merges identical text only; `off` keeps every sampled frame). Results appear in
`--format md` (an "On-screen text" section) and `--format json` (`on_screen`); `txt` and `srt` are
unchanged. A video with no speech but readable on-screen text succeeds. Not combinable with `--mp3`.

| `--ocr-engine` | Install | Notes |
|---|---|---|
| `rapidocr` (default) | `pip install 'igt[rapidocr]'` | much cleaner on social-video text; about 50 MB |
| `tesseract` | `apt install tesseract-ocr` / `brew install tesseract` | no Python dependency; noisy on stylised captions |

Both need `ffmpeg`. A missing tool exits 3 before anything is downloaded. Sampling is uncapped, so a
small `--ocr-every` on a long video produces many frames.

## Project-idea brief

`--format idea` writes a markdown brief seeded with the extracted caption, transcript and (with `--ocr`)
on-screen text: a requirements checklist to fill in, open questions, and brainstorm prompts that embed the
content so you can paste them into any LLM. It is a fixed template, not LLM output; nothing is sent
anywhere. With `--out` the file is `<shortcode>.md`.

`--idea-llm` (with `--format idea`) adds a "Generated analysis" section written by an LLM. Pick the backend with
`--llm-provider` and the model with `--llm-model`:

| `--llm-provider` | Default model | Needs | Data |
|---|---|---|---|
| `anthropic` (default) | `claude-sonnet-5-5` | `pip install 'igt[llm]'`, `ANTHROPIC_API_KEY` (environment only) | extracted caption, transcript and on-screen text are **sent to Anthropic** |
| `ollama` | `llama3.1:8b` | a running `ollama serve` and `ollama pull <model>`; `OLLAMA_HOST` if not `localhost:11434` | stays on your machine (unless `OLLAMA_HOST` points elsewhere) |

A missing key, package, server or model exits 3 before anything is downloaded; a request failure exits 6.

## Saving output

By default the result goes to stdout. To write a file instead, use `--out` or `--out-file` (mutually exclusive); `--mp3` also writes a file:

| Option | Writes to |
|---|---|
| `--out` | `<shortcode>.<format>` (e.g. `ABC123xyz.md`) in the output directory |
| `--out-file PATH` | `PATH`: relative to the output directory, or absolute |
| `--mp3` | audio only, no transcription: `<shortcode>.mp3` (or `--out-file PATH`) in the output directory; needs `ffmpeg` |

The output directory is `$IGT_OUT_ROOT` if set, otherwise the **current directory**. Missing parent
directories are created, the path is printed on success, and nothing is downloaded if the destination
is unwritable, a directory, or a symlink. It can never be inside this repository.

```bash
cd ~/notes
igt URL --format md --out                      # ./<shortcode>.md
igt URL --format md --out-file talk.md         # ./talk.md
igt URL --format md --out-file ~/x/talk.md     # absolute path
IGT_OUT_ROOT=~/transcripts igt URL --out       # ~/transcripts/<shortcode>.txt
```

Quote URLs containing `?` or `&` so the shell doesn't glob or background them.

Accepted URLs: `instagram.com/(reel|p|tv)/<id>/` (optionally with a `/<username>/` prefix);
`youtube.com/watch?v=<id>`, `youtube.com/shorts/<id>`, `youtu.be/<id>`; `facebook.com/reel/<id>/`,
`facebook.com/(<username>/)videos/<id>/`, `facebook.com/watch/?v=<id>`, `facebook.com/share/(r|v)/<code>/`,
`fb.watch/<code>`; or
`tiktok.com/@<username>/video/<id>/`, `vm.tiktok.com/<code>`, `vt.tiktok.com/<code>`. Tracking
parameters such as `?igsh=` or `&t=` are dropped.

## Environment

| Variable | Meaning |
|---|---|
| `IGT_OUT_ROOT` | Output directory for `--out` and relative `--out-file`. Optional (default: current directory). Must be outside this repository. |
| `IGT_COOKIES_FILE` | Netscape-format cookies file (same as `--cookies`). Must be outside this repository. |
| `ANTHROPIC_API_KEY` | API key for `--idea-llm` with the `anthropic` provider. Read from the environment only, never from argv. |
| `OLLAMA_HOST` | Ollama server for `--llm-provider ollama` (default `localhost:11434`). |

Cookies are credentials — keep the file out of the repo.
Keep API keys in a file outside the repo and load them with `set -a; source ~/keys/anthropic.key; set +a` (plain
`source` sets shell variables that `igt` cannot see unless the file uses `export`).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Transcript produced |
| 2 | Bad URL or usage |
| 3 | Configuration error (forbidden/unwritable output path, missing cookies file) |
| 4 | Download failed (login required, no video, rate limit, ...) |
| 5 | Transcription failed, or no speech detected |
| 6 | LLM request failed (`--idea-llm`) |
| 130 | Interrupted (Ctrl-C) |

`--format json` and `--format md` include the video's creator, upload date, duration, caption and hashtags
(taken from yt-dlp; fields the source site doesn't provide are left empty). `--cookies` and `--cookies-from` are
mutually exclusive; `--cookies-from` wins over `IGT_COOKIES_FILE`.

Errors go to stderr as `error: <message>`; stdout carries only the result.

## Versioning

[SemVer](https://semver.org/): `MAJOR.MINOR.PATCH`. Currently `0.x` — no stability guarantees yet, a
minor bump may still break things. `igt --version` reports the installed version; see
[CHANGELOG.md](CHANGELOG.md) for what changed in each release.

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

## Disclaimer

`igt` is an independent, unofficial tool with no affiliation to, endorsement by, or sponsorship
from Instagram/Meta, YouTube/Google, Facebook/Meta, or TikTok/ByteDance. All product names and
trademarks belong to their respective owners.

Only download and transcribe content you have the right to use. You are responsible for complying
with each platform's Terms of Service, applicable copyright law, and any content owner's rights;
this project provides no legal guidance on that. Provided under the MIT license, "as is," with no
warranty of any kind — see [LICENSE](LICENSE).
