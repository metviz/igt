# igt — Instagram/YouTube/Facebook/TikTok transcript CLI

`igt <url>` downloads an Instagram reel/post's, YouTube video's, Facebook reel/video's or TikTok video's
audio (yt-dlp) and transcribes it locally (faster-whisper).
Output: `txt | srt | json | md` to stdout, or to a file with `--out`. Standalone project; it began as the CLI
counterpart of a Chrome extension (separate repo) but shares no code with it. History: `docs/plans/`.

## Commands

```bash
uv sync                                   # create .venv, install deps
uv run pytest -q                          # unit tests (no network, no models)
uv run pytest --cov=igt --cov-fail-under=80
IGT_TEST_URL=<public reel> uv run pytest -m integration   # opt-in live smoke test
uv run igt --help
```

`uv` warns that `VIRTUAL_ENV` doesn't match the project env — harmless, ignore it.

## Layout

```
src/igt/
  url.py         parse_video_url -> ParsedUrl (Instagram + YouTube + Facebook + TikTok; strict host allow-list, canonical URL)
  models.py      Segment, Transcript (frozen dataclasses)
  formatters.py  to_txt / to_srt / to_json / to_md, FORMATS registry
  config.py      REPO_ROOT, outside(), env_path(), out_base() — the ONLY module that knows path policy
  download.py    Downloader protocol, YtDlpDownloader, Downloaded (audio path + metadata)
  transcribe.py  Transcriber protocol, FasterWhisperTranscriber (lazy model load)
  pipeline.py    generate(): parse -> download -> transcribe -> Transcript; temp dir always removed
  cli.py         argparse + main(); maps IgtError.exit_code to the process exit code
  errors.py      IgtError hierarchy, one exit_code per class
tests/           fakes.py (FakeDownloader/FakeTranscriber), one test_*.py per module, integration/ (opt-in)
```

Design: pure core + two I/O seams (`Downloader`, `Transcriber`) injected into `pipeline.generate()` and
`cli.main()`. Tests use fakes at the seams; never hit the network or load a model in unit tests.

## Hard rules

- **No output path may resolve inside this repo.**
  `--out`/relative `--out-file` use `IGT_OUT_ROOT`, else the current directory (changed 2026-10-02 at the user's request: was a hard failure when unset); either is rejected if inside the repo. Cookies (`--cookies`, `IGT_COOKIES_FILE`) are
  credentials: must exist and be outside the repo. Guarded by `config.outside()`; tests pin it.
- Output is validated (dir creatable + writable, target not a symlink) **before** any download.
- Secrets/cookies never go in the repo, argv values that are secrets, or git. `.gitignore` is defence in
  depth only — no `!` re-include rules.
- stdout carries only the result; errors go to stderr as `error: <message>`; no tracebacks for expected failures.
  yt-dlp's own logger is silenced (`_SilentLogger`) so igt owns stderr.
- Exit codes: 0 ok · 2 bad URL/usage · 3 config · 4 download · 5 transcription/no speech · 130 Ctrl-C.
  (`ApiError`/6 exists but is unused — dead code unless the optional API backend is built.)
- TDD: failing test first, watch it fail, minimal code, keep ≥80% coverage (currently ~98%).
- Immutable data (frozen dataclasses, tuples). Small files. No `print` outside `cli.py`.
- Commit messages: `<type>: <description>`; body ends with `developed with the help of AI assistance`.
  Never add `Co-Authored-By` or `Claude-Session` trailers.
- Never publish/push without confirming repo name and visibility first. No git remote is configured yet.

## Open items

- Live smoke test done (2026-09-27): a public reel and a public `/p/` post transcribe end to end, and
  `IGT_TEST_URL=<reel> pytest -m integration` passes. It found and fixed `/reels/` URLs and the CUDA
  `device="auto"` crash (Whisper is now pinned to cpu/int8; no `--device` flag).
- `--cookies-from chrome` loads cookies and exits 0 on Linux (needs `secretstorage`, now a Linux-only dep),
  but it has only been run on public posts. Not yet shown to get past a real login wall; needs a
  login-walled URL. Other browsers untested.
- The default `base` model garbles proper nouns (e.g. Kremlin, Murmansk); `--model small` untested.
- Deferred minors from the whole-branch review: Whisper hallucination on music-only clips ("Thank you.");
  bad `--language`/`--model` only detected after the download (exit 5, should be 2 at parse time);
  multi-video carousels download every video but transcribe only the first (`noplaylist` is ignored by the
  Instagram extractor); fallback error keeps yt-dlp's `ERROR:` prefix and rate-limit/deleted reels can read as
  "login required"; non-`DownloadError` from yt-dlp or a missing `filepath` can still traceback; SRT cue breaks
  if a segment contains a blank line; `ApiError` dead code / exit 1 undocumented in README;
  `REPO_ROOT` guard only accurate for an editable install.
- Optional, unbuilt: `--backend api` mirroring the extension's `POST /api/ext/v1/transcript` contract
  (Task 8 in `docs/plans/2026-09-27-igt-cli.md`) — only if a compatible server exists.

## Notes

- yt-dlp's extractors for these sites break periodically (TikTok's most often): `uv lock --upgrade-package yt-dlp`.
- A formatter hook (ruff/black) may rewrite files after edits; re-read a file before an `Edit` if an
  `old_string` fails to match.
- Only download content you have the right to use; respect each site's Terms of Service.
