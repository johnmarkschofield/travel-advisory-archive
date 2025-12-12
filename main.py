import feedparser
import json
import os
import re
from datetime import datetime

# Configuration
RSS_URL = "https://travel.state.gov/_layouts/15/sas/sp/rss.aspx?list=TravelAdvisories"
DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "current_advisories.json")
README_FILE = "README.md"

def fetch_advisories():
    print(f"Fetching RSS feed from: {RSS_URL}")
    feed = feedparser.parse(RSS_URL)

    advisories = []

    for entry in feed.entries:
        # Title format is usually: "Country Name - Level X: Reason"
        # We want to parse this to make it usable data
        title = entry.title
        link = entry.link
        pub_date = entry.published

        # Regex to extract Level
        level_match = re.search(r'Level (\d+)', title)
        level = int(level_match.group(1)) if level_match else 0

        # Clean up country name (Take everything before the dash)
        country = title.split('-')[0].strip()

        advisories.append({
            "country": country,
            "level": level,
            "full_title": title,
            "link": link,
            "date": pub_date
        })

    return advisories

def save_data(advisories):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Save the current state to JSON
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(advisories, f, indent=2)
    print(f"Saved {len(advisories)} advisories to {HISTORY_FILE}")

def update_readme(advisories):
    # Sort: Level 4 first (descending), then alphabetical by country
    sorted_advisories = sorted(advisories, key=lambda x: (-x['level'], x['country']))

    # Filter for Level 4 for the highlight section
    level_4 = [a for a in sorted_advisories if a['level'] == 4]

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

    md_content = f"""# 🌍 US State Department Travel Advisories

**Last Updated:** {timestamp}
**Total Advisories Tracked:** {len(advisories)}

The data below is automatically fetched from the [US State Department](https://travel.state.gov/).
Full data is archived in `data/current_advisories.json`.

---

## 🚨 Current Level 4: Do Not Travel
*There are currently **{len(level_4)}** destinations listed as Level 4.*

| Country | Date Issued | Link |
| :--- | :--- | :--- |
"""

    for item in level_4:
        md_content += f"| **{item['country']}** | {item['date']} | [Read Advisory]({item['link']}) |\n"

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
        save_data(data)
        update_readme(data)