Give me a summary of my newsboat feeds.

Steps:

1. Refresh the newsboat feeds. This can take 30-60 seconds depending on how many feeds I have. If it fails because newsboat is already running (lock file), tell me and stop — don't try to force it.

2. Query `~/.local/share/newsboat/cache.db` for unread items from the last $ARGUMENTS hours. If $ARGUMENTS is empty, default to 168 (1 week).

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

3. If there are more than 60 items, show me the count and ask whether to proceed, narrow the window, or filter to specific feeds before you summarize — summarizing hundreds of items blindly wastes tokens.

4. Group items by theme, not by feed. The same story often shows up across multiple outlets; consolidate those into one entry and list the sources together.

5. For each cluster, give me:
   - A 2-3 sentence summary in plain prose
   - Source links (feed name + URL)
   - Skip pure-headline duplicates where nothing adds signal

6. At the end, call out anything that looks genuinely important or unusual — the stuff I'd regret missing — in a short "worth a closer look" section.

Do NOT mark anything as read. Leave the `unread` column alone.

If the cache file isn't at `~/.local/share/newsboat/cache.db`, check `~/.newsboat/cache.db` and `~/.config/newsboat/cache.db` before giving up.
