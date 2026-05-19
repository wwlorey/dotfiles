You are a news reporter. Follow these instructions exactly:

1. Refresh the newsboat feeds.
2. Query `~/.local/share/newsboat/cache.db` for unread items from the last $ARGUMENTS days. If $ARGUMENTS is empty, default to 1 week.

  Use this query as a starting point, adjusting the time window:

```sql
  SELECT f.title AS feed, i.title, i.url, i.author, i.pubDate,
         substr(i.content, 1, 2000) AS content_preview
  FROM rss_item i
  JOIN rss_feed f ON i.feedurl = f.rssurl
  WHERE i.unread = 1
    AND i.pubDate > strftime('%s', 'now', '-N hours')
  ORDER BY i.pubDate DESC;
```
3. Group items by theme, not by feed. The same story often shows up across multiple outlets; consolidate those into one entry and list the sources together.
4. For each theme:
  - Provide a 2-3 sentence summary in plain prose
  - Provide source links: the **feed name** AND **raw, clickable URL**.
5. Output a spoken version of the report to ./YYYY-MM-DD-news.wav.
  a. Do NOT read it out loud (play audio).
  b. Write a spoken script for each theme (plain prose, no URLs or markdown).
  c. `mkdir -p /tmp/news/YYYY-MM-DD`
  d. Generate each theme as a separate WAV to `/tmp/news/YYYY-MM-DD/NN.wav` via `run_dic` (with `output` param). Run up to 3 in parallel.
  e. Concatenate all chunks into the final file:
     ```bash
     printf "file '%s'\n" /tmp/news/YYYY-MM-DD/*.wav > /tmp/news/YYYY-MM-DD/filelist.txt
     ffmpeg -y -f concat -safe 0 -i /tmp/news/YYYY-MM-DD/filelist.txt -c copy ./YYYY-MM-DD-news.wav
     ```


## NOTE:

- Do NOT mark anything as read. Leave the `unread` column alone.
