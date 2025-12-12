import feedparser
import requests
import json
import os
import re
import html2text
from datetime import datetime

# Configuration
RSS_URL = "https://travel.state.gov/_res/rss/TAsTWs.xml"
DATA_DIR = "data"
ADVISORY_DIR = "advisories"
HISTORY_FILE = os.path.join(DATA_DIR, "current_advisories.json")
README_FILE = "README.md"

# Browser headers to prevent blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def clean_filename(name):
    """Converts a country name into a safe filename (e.g. 'United Kingdom' -> 'united_kingdom.md')"""
    # Remove non-alphanumeric characters except spaces
    clean = re.sub(r'[^a-zA-Z0-9 ]', '', name)
    # Replace spaces with underscores and lowercase
    return clean.replace(' ', '_').lower() + ".md"

def fetch_advisories():
    print(f"Fetching RSS feed from: {RSS_URL}")

    try:
        response = requests.get(RSS_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        if len(feed.entries) == 0:
            print("WARNING: 0 entries found in feed.")
            return []

        advisories = []

        # Setup HTML to Markdown converter
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0 # Don't wrap text

        for entry in feed.entries:
            title = entry.title
            link = entry.link

            # Get the content/description
            # The RSS feed usually puts the text in 'summary' or 'description'
            raw_html = getattr(entry, 'summary', '') or getattr(entry, 'description', '')

            # Convert HTML content to Markdown
            markdown_text = h.handle(raw_html)

            if hasattr(entry, 'published'):
                pub_date = entry.published
            else:
                pub_date = "Unknown Date"

            # Extract Level
            level_match = re.search(r'Level (\d+)', title)
            level = int(level_match.group(1)) if level_match else 0

            # Extract Country Name
            country = title.split('-')[0].strip()
            if "Level" in country:
                country = country.split('Level')[0].strip()

            # Generate local filename
            filename = clean_filename(country)
            local_path = os.path.join(ADVISORY_DIR, filename)

            advisories.append({
                "country": country,
                "level": level,
                "full_title": title,
                "remote_link": link,
                "local_path": local_path,
                "filename": filename,
                "date": pub_date,
                "content_md": markdown_text
            })

        return advisories

    except Exception as e:
        print(f"Critical Error: {e}")
        return []

def save_advisories_locally(advisories):
    """Saves individual markdown files for each country."""
    if not os.path.exists(ADVISORY_DIR):
        os.makedirs(ADVISORY_DIR)

    # Clean up old files? (Optional: simplistic approach is just overwrite)

    for item in advisories:
        filepath = item['local_path']

        # Create the content for the individual country file
        file_content = f"""# {item['country']}

**Level {item['level']} Advisory**
**Date:** {item['date']}
**Source:** [State.gov Link]({item['remote_link']})

---

{item['content_md']}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(file_content)

    print(f"Saved {len(advisories)} local advisory files in /{ADVISORY_DIR}.")

def save_json_history(advisories):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # We remove the heavy content_md from the JSON to keep it light
    lightweight_list = [{k: v for k, v in a.items() if k != 'content_md'} for a in advisories]

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(lightweight_list, f, indent=2)

def update_readme(advisories):
    if not advisories:
        return

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

    md_content = f"""# 🌍 US State Department Travel Advisories Archive

**Last Updated:** {timestamp}
**Total Countries Tracked:** {len(advisories)}

This repository automatically archives travel advisories from the [US State Department](https://travel.state.gov/).
Click on a country to view the full archived text of the advisory.

---
"""

    # Loop through levels 1 to 4
    levels = {
        1: "Level 1: Exercise Normal Precautions",
        2: "Level 2: Exercise Increased Caution",
        3: "Level 3: Reconsider Travel",
        4: "Level 4: Do Not Travel",
        0: "Uncategorized / Other"
    }

    # Sort primarily by Country Name alphabetically
    advisories_sorted = sorted(advisories, key=lambda x: x['country'])

    for level_num in sorted(levels.keys()):
        # Filter for this level
        current_level_list = [a for a in advisories_sorted if a['level'] == level_num]

        if not current_level_list:
            continue

        header_icon = "🟢" if level_num == 1 else "🟡" if level_num == 2 else "🟠" if level_num == 3 else "🔴"

        md_content += f"\n## {header_icon} {levels[level_num]}\n"
        md_content += f"*Total: {len(current_level_list)} countries*\n\n"

        # Table Header
        md_content += "| Country | Date Issued | Local Archive |\n"
        md_content += "| :--- | :--- | :--- |\n"

        for item in current_level_list:
            # Link to the local file in the advisories/ folder
            # GitHub uses forward slashes for relative links
            link_path = f"advisories/{item['filename']}"
            md_content += f"| **{item['country']}** | {item['date']} | [📄 View Advisory]({link_path}) |\n"

    md_content += """
---
*Automated by GitHub Actions.*
"""

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print("README.md updated.")

if __name__ == "__main__":
    data = fetch_advisories()
    if data:
        save_advisories_locally(data)
        save_json_history(data)
        update_readme(data)