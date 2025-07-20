# LyricMiner

> A lightweight lyrics extractor for wordlists and analysis  
> **Author:** [cyto0x](https://github.com/cyto0x)

## Features
- Scrape lyrics from AZLyrics by artist name  
- Random delays & User‑Agent rotation to avoid blocks  
- CAPTCHA/redirect detection with clear instructions  
- Resume interrupted sessions automatically  
- Interactive song selection (ranges, all/none)  
- TXT or JSON output formats  
- Optional HTTP(S) proxy support  

## Installation

```bash
# Clone and install
git clone https://github.com/cyto0x/LyricMiner.git
cd LyricMiner
pip install -r requirements.txt
```

---

## Usage

```bash
# Extract all songs as TXT
python lyricminer.py -a "Artist Name"

# Resume last session
python lyricminer.py --resume

# First song only (test mode)
python lyricminer.py -a "Artist Name" --test

# JSON output via proxy
python lyricminer.py -a "Artist Name" --format json --proxy http://127.0.0.1:8080
```

---

## Outputs

- `lyrics_output/`  
  - `song_name.txt` or `.json` – individual lyrics files  
  - `combined_lyrics.txt` or `.json` – all lyrics concatenated  
  - `metadata.json` – artist, song list & timestamps  

---

## Requirements

- Python 3.6+  
- `requests`

```txt
requests
```
