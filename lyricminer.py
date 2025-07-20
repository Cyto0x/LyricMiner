#!/usr/bin/env python3
"""
LyricMiner - Lyrics Extractor
Author: cyto0x
"""
import argparse
import re
import requests
import urllib3
import time
import random
from urllib.parse import urljoin, urlparse
import json
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# List of common user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

def is_redirect_block(response):
    """Check if response indicates a blocking redirect"""
    if response.status_code in (301, 302, 303, 307, 308):
        # Check if redirected to a different domain
        original_domain = urlparse(response.url).netloc
        new_domain = urlparse(response.headers.get('Location', '')).netloc
        
        if new_domain and new_domain != original_domain:
            return True
    
    # Check for Cloudflare or other blocking pages
    if "cf-chl-bypass" in response.text or "captcha" in response.text.lower():
        return True
        
    return False

def extract_lyrics(html):
    """
    Extract lyrics from AZLyrics HTML content using verified regex pattern
    """
    pattern = re.compile(
        r'<!-- Usage of azlyrics\.com content by any third-party lyrics provider is prohibited by our licensing agreement\. Sorry about that\. -->\s*(.*?)\s*</div>',
        re.DOTALL
    )
    
    match = pattern.search(html)
    if not match:
        return None
        
    lyrics = match.group(1).strip()
    lyrics = re.sub(r'<br\s*/?>', '\n', lyrics)  # Convert <br> to newlines
    lyrics = re.sub(r'<[^>]+>', '', lyrics)       # Remove any remaining HTML tags
    
    return lyrics

def get_artist_url(artist_name, proxy=None):
    """Get the artist page URL from AZLyrics"""
    first_char = artist_name[0].lower()
    first_char = first_char if first_char.isalpha() else "19"
    url = f"https://www.azlyrics.com/{first_char}.html"
    
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    try:
        response = requests.get(url, proxies=proxies, verify=False, headers={
            "User-Agent": get_random_user_agent()
        }, allow_redirects=False)
        
        # Check for blocking redirect
        if is_redirect_block(response):
            print("✗ BLOCK DETECTED: You've been redirected to a CAPTCHA page")
            print("Please visit https://www.azlyrics.com in your browser,")
            print("complete the CAPTCHA, then try again later.")
            return None
            
        response.raise_for_status()
        
        # Find all artist links
        artist_links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', response.text)
        
        # Find matching artist (case-insensitive)
        normalized_name = artist_name.lower()
        for path, name in artist_links:
            if normalized_name == name.strip().lower():
                return urljoin("https://www.azlyrics.com/", path)
                
        return None
    except Exception as e:
        print(f"Error getting artist URL: {str(e)}")
        return None

def extract_song_urls(html_content):
    """Extract all song URLs from artist page"""
    # Regex to find song links: <div class="listalbum-item"><a href="SONG_URL"
    pattern = r'<div class="listalbum-item"><a href="([^"]+)"'
    song_paths = re.findall(pattern, html_content)
    
    # Filter out invalid URLs
    valid_paths = [path for path in song_paths if "javascript" not in path and "mailto" not in path]
    
    # Convert to absolute URLs
    base_url = "https://www.azlyrics.com"
    return [urljoin(base_url, path) for path in valid_paths]

def process_song(url, proxy, min_delay, max_delay, timeout=10):
    """Fetch and process a single song with random delay"""
    try:
        # Calculate random delay
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        
        proxies = {"http": proxy, "https": proxy} if proxy else None
        response = requests.get(
            url, 
            proxies=proxies, 
            verify=False,
            headers={"User-Agent": get_random_user_agent()},
            timeout=timeout,
            allow_redirects=False
        )
        
        # Check for blocking redirect
        if is_redirect_block(response):
            print(f"✗ BLOCK DETECTED while accessing {url}")
            print("Please visit https://www.azlyrics.com in your browser,")
            print("complete the CAPTCHA, then try again later.")
            return None
            
        response.raise_for_status()
        
        lyrics = extract_lyrics(response.text)
        if lyrics:
            print(f"✓ Extracted lyrics from {url.split('/')[-1]} (Delay: {delay:.1f}s)")
            return lyrics
        else:
            print(f"× Could not extract lyrics from {url}")
            return None
            
    except Exception as e:
        print(f"! Error processing {url}: {str(e)}")
        return None

def save_state(artist, song_urls, processed_index, output_dir):
    """Save progress state to resume later"""
    state = {
        "artist": artist,
        "song_urls": song_urls,
        "processed_index": processed_index,
        "output_dir": output_dir
    }
    
    with open(os.path.join(output_dir, "state.json"), "w") as f:
        json.dump(state, f)

def load_state(output_dir):
    """Load progress state if exists"""
    state_file = os.path.join(output_dir, "state.json")
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return None

def interactive_song_selection(song_urls):
    """Let user select which songs to process"""
    print("\n=== SONG SELECTION ===")
    print(f"Found {len(song_urls)} songs. Select which ones to process:")
    
    # Display songs with numbers
    for i, url in enumerate(song_urls, 1):
        song_name = url.split("/")[-1].replace(".html", "")
        print(f"{i}. {song_name}")
    
    print("\nEnter song numbers (comma separated) or ranges (e.g., 1-5)")
    print("Type 'all' for all songs or 'none' to skip")
    selection = input("Your selection: ").strip().lower()
    
    if selection == "all":
        return song_urls
    elif selection == "none":
        return []
    
    selected_urls = []
    try:
        # Process range selections (e.g., 1-5, 8, 10-12)
        parts = selection.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                start, end = map(int, part.split("-"))
                selected_urls.extend(song_urls[start-1:end])
            else:
                index = int(part) - 1
                if 0 <= index < len(song_urls):
                    selected_urls.append(song_urls[index])
    except ValueError:
        print("Invalid selection. Processing all songs.")
        return song_urls
    
    return selected_urls

def main():
    parser = argparse.ArgumentParser(description="LyricMiner AZLyrics Lyrics Extractor")
    parser.add_argument("-a", "--artist", help="Artist name (required unless resuming)")
    parser.add_argument("--proxy", help="Proxy address (e.g., http://127.0.0.1:8080)")
    parser.add_argument("-o", "--output", default="lyrics_output", help="Output directory name")
    parser.add_argument("--min-delay", type=float, default=3.0, help="Minimum delay between requests in seconds")
    parser.add_argument("--max-delay", type=float, default=10.0, help="Maximum delay between requests in seconds")
    parser.add_argument("--test", action="store_true", help="Test mode: extract only first song")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    parser.add_argument("--format", choices=["txt", "json"], default="txt", help="Output format")
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Try to resume from previous state
    state = None
    if args.resume:
        state = load_state(args.output)
        if state:
            print(f"Resuming previous session for {state['artist']}")
    
    if state:
        artist = state["artist"]
        song_urls = state["song_urls"]
        start_index = state["processed_index"] + 1
    else:
        if not args.artist:
            print("Artist name is required when not resuming")
            return
            
        artist = args.artist
        start_index = 0
        
        # Get artist page URL
        print(f"Searching for artist: {artist}")
        artist_url = get_artist_url(artist, args.proxy)
        if not artist_url:
            print(f"Artist '{artist}' not found")
            return
        print(f"Found artist page: {artist_url}")

        # Fetch artist page
        proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
        try:
            print("Fetching artist song list...")
            response = requests.get(artist_url, proxies=proxies, verify=False, headers={
                "User-Agent": get_random_user_agent()
            }, allow_redirects=False)
            
            # Check for blocking redirect
            if is_redirect_block(response):
                print("✗ BLOCK DETECTED: You've been redirected to a CAPTCHA page")
                print("Please visit https://www.azlyrics.com in your browser,")
                print("complete the CAPTCHA, then try again later.")
                return
                
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching artist page: {str(e)}")
            return

        # Extract song URLs
        song_urls = extract_song_urls(response.text)
        
        if not song_urls:
            print(f"No songs found for {artist}")
            return
        
        print(f"Found {len(song_urls)} songs for {artist}")
        
        # Interactive song selection
        song_urls = interactive_song_selection(song_urls)
        if not song_urls:
            print("No songs selected. Exiting.")
            return
            
        # Save initial state
        save_state(artist, song_urls, -1, args.output)
    
    # Test mode: process only first song
    if args.test:
        print("\n=== TEST MODE: EXTRACTING FIRST SONG ONLY ===")
        song_urls = song_urls[:1]
        start_index = 0
    
    print(f"\nStarting lyrics extraction with random delay between {args.min_delay}-{args.max_delay} seconds...")
    
    # Process songs sequentially with random delays
    all_lyrics = []
    metadata = []
    
    for i in range(start_index, len(song_urls)):
        url = song_urls[i]
        song_name = url.split("/")[-1].replace(".html", "")
        print(f"\nProcessing song {i+1}/{len(song_urls)}: {song_name}")
        
        lyrics = process_song(url, args.proxy, args.min_delay, args.max_delay)
        if lyrics:
            # Save individual song file
            song_filename = re.sub(r'[^\w\-_\. ]', '_', song_name) + f".{args.format}"
            song_path = os.path.join(args.output, song_filename)
            
            if args.format == "json":
                song_data = {
                    "artist": artist,
                    "song": song_name,
                    "url": url,
                    "lyrics": lyrics
                }
                with open(song_path, "w", encoding="utf-8") as f:
                    json.dump(song_data, f, indent=2)
            else:
                with open(song_path, "w", encoding="utf-8") as f:
                    f.write(lyrics)
            
            all_lyrics.append(lyrics)
            metadata.append({
                "artist": artist,
                "song": song_name,
                "url": url,
                "file": song_filename
            })
        
        # Update state after each song
        save_state(artist, song_urls, i, args.output)
    
    # Save combined wordlist
    if all_lyrics:
        combined_path = os.path.join(args.output, f"combined_lyrics.{args.format}")
        if args.format == "json":
            combined_data = {
                "artist": artist,
                "total_songs": len(all_lyrics),
                "songs": metadata,
                "all_lyrics": "\n\n".join(all_lyrics)
            }
            with open(combined_path, "w", encoding="utf-8") as f:
                json.dump(combined_data, f, indent=2)
        else:
            with open(combined_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(all_lyrics))
        
        # Save metadata
        metadata_path = os.path.join(args.output, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({
                "artist": artist,
                "total_songs": len(all_lyrics),
                "songs": metadata,
                "created": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, indent=2)
        
        # Remove state file on successful completion
        state_file = os.path.join(args.output, "state.json")
        if os.path.exists(state_file):
            os.remove(state_file)
        
        print(f"\nSuccess! Extracted {len(all_lyrics)} songs.")
        print(f"Output directory: {args.output}")
    else:
        print("\nNo lyrics were extracted. Please check the error messages.")

if __name__ == "__main__":
    main()
