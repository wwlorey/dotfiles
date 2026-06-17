---
name: youtube-transcript
description: Working with the contents of a YouTube video — fetching a transcript, summarizing, quoting, extracting notes, answering questions about what was said, or any task where the source material is a YT URL. Consult whenever you have a YouTube URL in hand for any reason — the user shared a link, asked about a video by name, or a search result surfaced one that would answer the question — even when the word "transcript" is never mentioned (e.g. "summarize this", "what does he say about X", "pull the key points").
---

# YouTube Transcript

Use the `transcribe-yt` CLI to pull a transcript, then Read the resulting file.

## Steps

1. Run `transcribe-yt <youtube-url>` from `$TMPDIR/claude` so the transcript
   does not land in the user's working directory.
2. Parse the `Title:` and `Saved to <filename>.txt` lines from stdout — keep
   the title for the sources section, and the path (relative to where you
   ran the command) is the transcript.
3. Read the file with the Read tool. Now do whatever the user asked
   (summarize, quote, answer questions, etc.).
4. End your reply with a `Sources:` section listing every video you pulled.
   The URL must appear as a bare URL (NOT wrapped in markdown `[text](url)`
   syntax) so the terminal auto-linkifies it and the user can click it:

   ```
   Sources:
   - <title> — https://www.youtube.com/watch?v=...
   ```

   Include this even for single-video tasks — the user wants to click
   through to the source.

```bash
cd "$TMPDIR/claude" && transcribe-yt "https://www.youtube.com/watch?v=..."
```

## Notes

- The script slugifies the video title for the filename; do not guess it,
  read the `Saved to` line.
- Transcripts are plain text with no timestamps. If the user wants
  timestamps, say so — this script does not provide them.
- Delete the file from `$TMPDIR/claude` when done unless the user asked
  to keep it.
