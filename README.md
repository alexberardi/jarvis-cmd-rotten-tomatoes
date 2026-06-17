# jarvis-cmd-rotten-tomatoes

Rotten Tomatoes command for [Jarvis](https://github.com/alexberardi/jarvis-node-setup).

Search for movies and TV shows, get Tomatometer scores, cast info, Certified Fresh status, and browse what's in theaters.

This is an unofficial integration with Rotten Tomatoes — no API key required.

## ⚠️ Disclaimer

This command is an **unofficial** integration and is **not affiliated with, endorsed by, or supported by Rotten Tomatoes or Fandango**. It works by reading the public Rotten Tomatoes website rather than an official API.

- Using it may violate the [Rotten Tomatoes Terms of Service](https://www.rottentomatoes.com/policies/terms-and-policies). You are responsible for ensuring your use complies with their terms.
- It is **best-effort and may break at any time** if the Rotten Tomatoes website changes. No accuracy, availability, or stability guarantees are made.
- All movie/TV data and trademarks (including "Rotten Tomatoes", "Tomatometer", and "Certified Fresh") belong to their respective owners.

Use at your own risk.

## Install

```bash
python scripts/command_store.py install --url https://github.com/alexberardi/jarvis-cmd-rotten-tomatoes
```

## Voice Examples

- "What's the rating for The Shawshank Redemption?"
- "Is Dune 2 any good?"
- "What movies are in theaters right now?"

## Dependencies

- `httpx`
