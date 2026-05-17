import json
import csv
import urllib.request
import os
from io import StringIO

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON = os.path.join(BASE_DIR, 'meta', 'pp_onepacee.json')
BASE_META_URL = "https://fedew04.github.io/OnePaceStremio/meta/series/pp_onepace.json"

SHEET_ID = "1M0Aa2p5x7NioaH9-u8FyHq6rH3t5s6Sccs8GoC6pHAM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# URL to the official properties file
PROPERTIES_URL = "https://raw.githubusercontent.com/one-pace/one-pace-public-subtitles/main/main/title.properties"

# --- Load Central Config ---
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)
ARC_PREFIXES = CONFIG["ARC_MAP"]
TOTAL_SEASONS = CONFIG["TOTAL_SEASONS"]

def clean_string(s):
    """Removes spaces, dashes, apostrophes, and periods for exact matching."""
    return str(s).lower().replace(" ", "").replace("-", "").replace("'", "").replace(".", "")

def get_titles_from_properties(config_arc_map):
    """Fetches the official titles from the GitHub properties file."""
    print("Fetching official titles from One Pace GitHub...")
    try:
        req = urllib.request.urlopen(PROPERTIES_URL, timeout=10)
        lines = req.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Failed to fetch properties: {e}")
        return {}, {}

    id_to_title = {}
    key_to_title = {}

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, title = line.split("=", 1)
        
        # Clean the title: Strip whitespace and replace all double quotes with single quotes
        title = title.strip().replace('\\"', "'").replace('"', "'")
        
        if not title: 
            continue

        # e.g., "specials_04": "One Piece Fan Letter"
        original_key = key.split(".")[0]
        key_to_title[original_key] = title 

        raw_prefix, raw_ep = original_key.split("_")
        ep_num_int = int(raw_ep)

        clean_prefix = raw_prefix.lower().replace(" ", "")
        mapped_prefix = config_arc_map.get(clean_prefix, raw_prefix.upper())
        video_id = f"{mapped_prefix}_{ep_num_int}"

        id_to_title[video_id] = title

    return id_to_title, key_to_title

def main():
    print("1. Fetching original JSON from fedew04...")
    try:
        req = urllib.request.urlopen(BASE_META_URL, timeout=10)
        data = json.loads(req.read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to download base JSON: {e}")
        return

    print("2. Fetching descriptions from Google Sheets...")
    try:
        req = urllib.request.urlopen(CSV_URL, timeout=10)
        csv_content = req.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to download spreadsheet: {e}")
        return

    # Build description dictionaries
    descriptions_map = {}
    title_to_desc = {} # NEW: Fallback map based on exact English Title
    
    reader = csv.DictReader(StringIO(csv_content))
    for row in reader:
        arc_title = row.get("arc_title", "").strip()
        arc_part = row.get("arc_part", "").strip()
        title_en = row.get("title_en", "").strip()
        desc = row.get("description_en", "").strip()

        if not desc:
            continue

        # 1. Save by EXACT title (cleaning quotes to match properties file)
        if title_en:
            clean_title_en = title_en.replace('\\"', "'").replace('"', "'")
            title_to_desc[clean_title_en] = desc

        # 2. Save by ID mapping
        if arc_title and arc_part:
            clean_arc = clean_string(arc_title)
            if clean_arc in ARC_PREFIXES:
                matched_prefix = ARC_PREFIXES[clean_arc]
                try:
                    arc_part_str = str(int(arc_part))
                except ValueError:
                    arc_part_str = arc_part 

                video_id = f"{matched_prefix}_{arc_part_str}"
                descriptions_map[video_id] = desc

    print("3. Getting official titles from properties...")
    titles_map, key_to_title = get_titles_from_properties(ARC_PREFIXES)

    print("4. Loading specials.json configuration...")
    try:
        SPECIALS_PATH = os.path.join(BASE_DIR, 'meta', 'specials.json')
        with open(SPECIALS_PATH, 'r', encoding='utf-8') as f:
            specials_config = json.load(f)
            
        specials_by_id = {}
        for spec_key, spec_val in specials_config.items():
            vid_id = spec_val["id"]
            spec_val["original_key"] = spec_key # Keep track of the key (e.g. specials_04)
            specials_by_id[vid_id] = spec_val
            
    except FileNotFoundError:
        print("specials.json not found. Proceeding without special reordering.")
        specials_by_id = {}
    
    print("4.5. Loading thumbnails.json configuration...")
    try:
        THUMBNAILS_PATH = os.path.join(BASE_DIR, 'meta', 'thumbnails.json')
        with open(THUMBNAILS_PATH, 'r', encoding='utf-8') as f:
            thumbnails_map = json.load(f)
    except FileNotFoundError:
        print("thumbnails.json not found. Proceeding without custom thumbnails.")
        thumbnails_map = {}
        
    print("5. Applying transformations, titles, and injecting specials...")
    meta = data.get("meta", {})
    
    # Static Data Injection
    meta.update({
        "id": "pp_onepacee",
        "poster": "https://cdn.jsdelivr.net/gh/6ip/onepace-assets-prm@main/public/poster.jpg",
        "background": "https://cdn.jsdelivr.net/gh/6ip/onepace-assets-prm@main/public/background_pace.jpg",
        "logo": "https://cdn.jsdelivr.net/gh/6ip/onepace-assets-prm@main/public/logo.png",
        "description": "Experience One Piece without the filler. This manga-accurate cut removes padded scenes, saving you hundreds of hours while staying true to Oda's original vision.",
        "releaseInfo": "1999-",
        "year": "1999-",
        "imdbRating": "9.0",
        "country": "Japan",
        "released": "1999-10-20T00:00:00.000Z",
        "genres": ["Animation", "Action", "Adventure"],
        "cast": ["Mayumi Tanaka", "Akemi Okamura", "Tony Beck"]
    })
    
    meta["links"] = [
        {"name": "9.0", "category": "imdb", "url": "https://imdb.com/title/tt0388629"},
        {"name": "Animation", "category": "Genres", "url": "stremio:///discover/https%3A%2F%2Fv3-cinemeta.strem.io%2Fmanifest.json/series/top?genre=Animation"},
        {"name": "Action", "category": "Genres", "url": "stremio:///discover/https%3A%2F%2Fv3-cinemeta.strem.io%2Fmanifest.json/series/top?genre=Action"},
        {"name": "Adventure", "category": "Genres", "url": "stremio:///discover/https%3A%2F%2Fv3-cinemeta.strem.io%2Fmanifest.json/series/top?genre=Adventure"},
        {"name": "Mayumi Tanaka", "category": "Cast", "url": "stremio:///search?search=Mayumi%20Tanaka"},
        {"name": "Akemi Okamura", "category": "Cast", "url": "stremio:///search?search=Akemi%20Okamura"},
        {"name": "Tony Beck", "category": "Cast", "url": "stremio:///search?search=Tony%20Beck"}
    ]

    meta["seasons"] = [
        {
            "season": i,
            "poster": f"https://cdn.jsdelivr.net/gh/6ip/onepace-assets-prm@main/public/poster-s/poster-s{str(i).zfill(2)}.jpg"
        } for i in range(1, TOTAL_SEASONS + 1)
    ]

    desc_count = 0
    normal_videos = []
    special_videos_extracted = []

    # FIRST PASS: Clean IDs, override titles, set descriptions, filter configured specials
    for video in meta.get("videos", []):
        vid_id = video.get("id", "")
        if not str(vid_id).startswith("pp_"):
            vid_id = f"{vid_id}"
            video["id"] = vid_id
            
        # Override Title from Properties
        if vid_id in titles_map:
            video["title"] = titles_map[vid_id]

        season_num = video.get("season")
        
        # --- NEW: Thumbnail Priority Logic (Normal Videos) ---
        if vid_id in thumbnails_map:
            video["thumbnail"] = thumbnails_map[vid_id]
        elif season_num and 1 <= season_num <= TOTAL_SEASONS:
            s_padded = str(season_num).zfill(2)
            video["thumbnail"] = f"https://images.weserv.nl/?url=cdn.jsdelivr.net/gh/6ip/onepace-assets-prm@main/public/poster-s/poster-s{s_padded}.jpg&w=1280&h=720&fit=cover&a=center"
        else:
            video["thumbnail"] = "https://image.tmdb.org/t/p/w500/iN5LKyvyWUWwqbjaQfKFXoo8mch.jpg"

        # Inject Descriptions (Try ID map first, then Title map)
        clean_vid_title = video.get("title", "").replace('\\"', "'").replace('"', "'")
        
        if vid_id in descriptions_map:
            video["description"] = descriptions_map[vid_id]
            video["overview"] = descriptions_map[vid_id]
            desc_count += 1
        elif clean_vid_title in title_to_desc:
            video["description"] = title_to_desc[clean_vid_title]
            video["overview"] = title_to_desc[clean_vid_title]
            desc_count += 1

        if vid_id in specials_by_id:
            special_videos_extracted.append(video)
        else:
            normal_videos.append(video)

    # CONFIGURED SPECIALS: Create any missing specials defined in specials.json
    found_spec_ids = {v["id"] for v in special_videos_extracted}
    processed_original_keys = set()
    
    for spec_id, spec_val in specials_by_id.items():
        orig_key = spec_val["original_key"]
        processed_original_keys.add(orig_key)
        
        if spec_id not in found_spec_ids:
            spec_title = spec_val.get("custom_title", key_to_title.get(orig_key, "Special Episode"))
            # Try ID, then Title fallback
            desc = descriptions_map.get(spec_id, title_to_desc.get(spec_title, ""))
            if desc:
                desc_count += 1
                
            new_special = {
                "id": spec_id,
                "title": spec_title,
                "description": desc,
                "overview": desc,
                "thumbnail": "https://image.tmdb.org/t/p/w500/iN5LKyvyWUWwqbjaQfKFXoo8mch.jpg"
            }
            special_videos_extracted.append(new_special)

    # UNCONFIGURED SPECIALS AUTO-CATCHER
    # Finds any special in title.properties not mentioned in specials.json and auto-adds to Season 0
    all_property_keys = key_to_title.keys()
    for prop_key in all_property_keys:
        if prop_key.startswith("specials_") and prop_key not in processed_original_keys:
            raw_prefix, raw_ep = prop_key.split("_")
            fallback_id = f"{raw_prefix.upper()}_{int(raw_ep)}"
            spec_title = key_to_title[prop_key]
            
            # Fetch description strictly by exact title matching
            desc = title_to_desc.get(spec_title, "")
            if desc:
                desc_count += 1

            unconfigured_special = {
                "id": fallback_id,
                "title": f"[Special] {spec_title}",
                "description": desc,
                "overview": desc,
                "season": 0, # Send unconfigured straight to Season 0
                "episode": int(raw_ep),
                "thumbnail": thumbnails_map.get(fallback_id, "https://image.tmdb.org/t/p/w500/iN5LKyvyWUWwqbjaQfKFXoo8mch.jpg"),
            }
            normal_videos.append(unconfigured_special)

    # SECOND PASS: Re-inject the configured specials at the end of their assigned seasons
    for spec_vid in special_videos_extracted:
        vid_id = spec_vid["id"]
        target_season = specials_by_id[vid_id]["season"]
        title_prefix = specials_by_id[vid_id]["title_start"]
        custom_thumb = specials_by_id[vid_id].get("thum") # NEW: Extract the custom thumbnail if it exists

        original_title = spec_vid.get("title", "")
        if not original_title.startswith(title_prefix.strip()):
            spec_vid["title"] = f"{title_prefix}{original_title}"

        spec_vid["season"] = target_season

        # --- NEW: 4-Tier Thumbnail Priority Logic (Specials) ---
        if vid_id in thumbnails_map:
            # Priority 1: Custom thumbnail from thumbnails.json
            spec_vid["thumbnail"] = thumbnails_map[vid_id]
        elif custom_thumb:
            # Priority 2: Custom thumbnail from specials.json
            spec_vid["thumbnail"] = custom_thumb
        elif 1 <= target_season <= TOTAL_SEASONS:
            # Priority 3: Season-specific poster
            s_padded = str(target_season).zfill(2)
            spec_vid["thumbnail"] = f"https://images.weserv.nl/?url=cdn.jsdelivr.net/gh/6ip/onepace-assets-prm@main/public/poster-s/poster-s{s_padded}.jpg&w=1280&h=720&fit=cover&a=center"
        else:
            # Priority 4: Fallback TMDB background
            spec_vid["thumbnail"] = "https://image.tmdb.org/t/p/w500/iN5LKyvyWUWwqbjaQfKFXoo8mch.jpg"

        # Find the max episode number currently existing in the target season
        episodes_in_target = [v.get("episode", 0) for v in normal_videos if v.get("season") == target_season]
        highest_ep = max(episodes_in_target) if episodes_in_target else 0

        spec_vid["episode"] = highest_ep + 1
        normal_videos.append(spec_vid)

    # Final Sort to ensure the UI looks clean
    normal_videos.sort(key=lambda x: (x.get("season", 0), x.get("episode", 0)))
    meta["videos"] = normal_videos

    print("6. Saving fully assembled JSON...")
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"\nDone! Saved to {OUTPUT_JSON}.")
    print(f"Descriptions matched and injected: {desc_count}")
    print(f"Specials safely reordered/injected: {len(special_videos_extracted)}")

if __name__ == "__main__":
    main()