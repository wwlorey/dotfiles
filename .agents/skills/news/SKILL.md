---
name: news
description: Producing a news report from the user's newsboat feeds — grouping unread items by theme across outlets and rendering both a written summary and a spoken WAV. Consult whenever the user asks for the news, a news report, a catch-up on what they missed, "what's happening", or anything that implies pulling recent unread items from their RSS/newsboat feeds. Even casual phrasings like "any news?" or "what'd I miss this week" count.
---

# News

Refresh the user's newsboat feeds, group unread items by theme, write a short summary per theme, and render the report as both text (in the reply) and a spoken WAV file in the working directory.

## Steps

1. **Refresh feeds.** Run newsboat to pull the latest items.
2. **Query unread items.** Read from `~/.local/share/newsboat/cache.db`. Window defaults to 1 week — adjust if the user gave a different duration.

   ```sql
   SELECT f.title AS feed, i.title, i.url, i.author, i.pubDate,
          substr(i.content, 1, 2000) AS content_preview
   FROM rss_item i
   JOIN rss_feed f ON i.feedurl = f.rssurl
   WHERE i.unread = 1
     AND i.pubDate > strftime('%s', 'now', '-N hours')
   ORDER BY i.pubDate DESC;
   ```

3. **Group by theme, not feed.** The same story shows up across multiple outlets — consolidate to one entry and list the sources together.
4. **For each theme, produce:**
   - A 2-3 sentence summary in plain prose.
   - Source links: the feed name **and** the raw, clickable URL (bare URL — do not wrap in markdown `[text](url)` syntax, the terminal auto-linkifies bare URLs).
5. **Render the spoken version** to `./YYYY-MM-DD-news.wav`:
   1. Write a spoken script for each theme — plain prose, no URLs, no markdown.
   2. `mkdir -p /tmp/news/YYYY-MM-DD`
   3. Generate each theme as a separate WAV at `/tmp/news/YYYY-MM-DD/NN.wav` using the voice skill's audio file render mode (pass `output: "/tmp/news/YYYY-MM-DD/NN.wav"`). Run up to 3 in parallel.
   4. Concatenate the chunks into the final file:
      ```bash
      printf "file '%s'\n" /tmp/news/YYYY-MM-DD/*.wav > /tmp/news/YYYY-MM-DD/filelist.txt
      ffmpeg -y -f concat -safe 0 -i /tmp/news/YYYY-MM-DD/filelist.txt -c copy ./YYYY-MM-DD-news.wav
      ```
   5. Do **not** play the audio — just save the file. Surface it per MEMENTO's rule (`wav: file:///…`).

## Rules

- **Do NOT mark anything as read.** Leave the `unread` column alone — the user reads items themselves in newsboat.
- Default window is 1 week; if the user said something like "today" or "the last 3 days", convert to hours for the SQL filter.
- The written report and the spoken WAV stay in sync — same themes, same order, same emphasis. The WAV is just the prose version without URLs.
