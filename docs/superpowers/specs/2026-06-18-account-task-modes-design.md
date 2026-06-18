# Account Task Modes Design

Date: 2026-06-18

## Goal

Add clear task modes for account-level Douyin video archiving. The user wants to process every video under a Douyin account and save readable text locally. There are two user-facing outcomes:

- `transcript`: produce a smooth, readable original transcript.
- `summary`: produce core viewpoints plus the smooth, readable original transcript.

Both modes use AI cleanup. There is no mode that publishes raw ASR text as the final article.

## Definitions

### Transcript Mode

`transcript` converts each video into a readable original transcript.

Pipeline:

```text
account URL
  -> enumerate video URLs
  -> download video/audio
  -> ASR raw transcript
  -> AI cleanup for typos, wrong words, bad sentences, and punctuation
  -> Markdown article with cleaned transcript
```

Final article body:

```markdown
## 原文

（AI 清洗后的顺畅原文）
```

The AI cleanup must preserve the original meaning. It may correct obvious ASR mistakes, punctuation, sentence breaks, filler duplication, and malformed phrasing, but it must not add new facts or rewrite the speaker's intent.

### Summary Mode

`summary` converts each video into core viewpoints plus the readable transcript.

Pipeline:

```text
account URL
  -> enumerate video URLs
  -> download video/audio
  -> ASR raw transcript
  -> AI cleanup for readable transcript
  -> AI summary of core viewpoints
  -> Markdown article with core viewpoints and cleaned transcript
```

Final article body:

```markdown
## 核心观点

（AI 提炼的视频主要观点）

## 原文

（AI 清洗后的顺畅原文）
```

The summary should focus on the video's core claims, opinions, reasoning, examples, and conclusions. It should be concise and grounded only in the transcript.

## CLI Shape

The account workflow should expose one account command with a mode option:

```powershell
pullpull account <账号主页URL> --mode transcript
pullpull account <账号主页URL> --mode summary
```

Default mode:

```text
transcript
```

Rationale: transcript mode creates the local readable source archive first. Summary mode can be run when the user wants higher-level analysis.

## Intermediate Files

For each video, preserve enough intermediate data to support retry and later reprocessing:

- raw ASR transcript: the unedited speech-to-text output
- cleanup request/response data: enough context to rerun or audit AI cleanup
- source metadata: video ID, URL, title, author, published date when available

The final Markdown should show only user-facing content: source metadata, `## 原文`, and optionally `## 核心观点`.

## Account Batch Behavior

The account command should:

1. Enumerate video URLs from the account homepage.
2. Process videos one by one through the existing single-video pipeline.
3. Maintain an index for deduplication and resume.
4. Skip already completed videos unless the user asks to rerun.
5. Record failures per video without aborting the whole batch.
6. Avoid bypassing login, captcha, risk controls, or access restrictions.

Cookies may be supported with the existing pattern:

```powershell
--cookies-from-browser chrome
```

This is only for content the user can legally access in their own browser session.

## AI Contract

AI output should use structured JSON internally.

For `transcript`:

```json
{
  "cleaned_transcript": "..."
}
```

For `summary`:

```json
{
  "core_viewpoints": "...",
  "cleaned_transcript": "..."
}
```

Validation rules:

- `cleaned_transcript` must be non-empty in both modes.
- `core_viewpoints` must be non-empty in summary mode.
- AI must not invent facts outside the transcript.
- If the transcript is empty or unusable, mark the video failed with a clear reason.

## Existing Code Fit

The current project already has useful pieces:

- `pullpull.pull.collect()` downloads and transcribes one video.
- `pullpull.article.RefineRequest` and finalization patterns already model AI cleanup and article rendering.
- `dfa_cli.py` has a single-video state-machine flow that can inform deduplication and resume behavior.

The account workflow should reuse those pieces rather than create a separate download/transcription path.

## Out Of Scope

This design does not include:

- reading private drafts or creator-backend original scripts
- OCR of on-screen subtitles
- reposting or uploading video content
- bypassing platform access controls
- a GUI

## Acceptance Criteria

- A user can choose `--mode transcript` or `--mode summary`.
- Transcript mode outputs Markdown with cleaned `## 原文`.
- Summary mode outputs Markdown with `## 核心观点` and cleaned `## 原文`.
- Raw ASR text remains available for retry/audit but is not the final user-facing article.
- The batch process can resume and skip already completed videos.
- Per-video failures are recorded without stopping unrelated videos.
