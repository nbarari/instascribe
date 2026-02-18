# Instascribe: LLM Dataset Optimizer
# Copyright (C) 2026 Nicholas Barari
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import os
import re
from datetime import datetime

def fix_encoding(text):
    """Resolves the 'mojibake' encoding error common in Instagram exports."""
    if text is None: return ""
    try:
        return text.encode('latin1').decode('utf8')
    except:
        return text

def clean_url(url):
    """Strips tracking parameters from shared URLs."""
    if not url: return ""
    return url.split('?')[0]

def format_duration(seconds):
    """Converts call duration to readable format or identifies missed calls."""
    if seconds == 0:
        return "MISSED/CANCELLED"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

def clean_caption(text):
    """Removes hashtags and marketing fluff from shared content captions."""
    text = re.sub(r'#\w+', '', text)
    spam_phrases = ["follow @", "dm for", "credit:", "tag a", "repost", "link in bio", "subscribe"]
    lines = text.split('\n')
    cleaned_lines = [l for l in lines if not any(p in l.lower() for p in spam_phrases)]
    return " ".join(cleaned_lines).strip()

def find_conversations(root_path):
    """Recursively scans for Instagram message JSON files and extracts metadata."""
    valid_folders = []
    print("Scanning for conversations...")
    for root, dirs, files in os.walk(root_path):
        if "message_1.json" in files:
            try:
                with open(os.path.join(root, "message_1.json"), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    title = fix_encoding(data.get('title', 'Unknown'))
                    participants = [fix_encoding(p['name']) for p in data.get('participants', [])]
                    valid_folders.append({
                        'path': root, 
                        'title': title, 
                        'folder_id': os.path.basename(root),
                        'participants': participants
                    })
            except:
                continue
    return sorted(valid_folders, key=lambda x: x['title'].lower())

def process_single_conversation(conv, user_name, self_aware_input, meta_choice, meta_labels, global_output_path):
    input_folder = conv['path']
    folder_id_name = conv['folder_id']
    target_thread_title = conv['title']

    json_files = sorted([f for f in os.listdir(input_folder) if f.endswith('.json') and f.startswith('message_')])
    all_messages = []
    for file_name in json_files:
        with open(os.path.join(input_folder, file_name), 'r', encoding='utf-8') as f:
            data = json.load(f)
            if fix_encoding(data.get('title')) == target_thread_title:
                if 'messages' in data: all_messages.extend(data['messages'])

    all_messages.sort(key=lambda x: x.get('timestamp_ms', 0))

    cleaned_output = []
    last_date, last_sender, last_timestamp = None, None, 0
    GAP_THRESHOLD_MS = 6 * 3600 * 1000 
    GROUPING_THRESHOLD_MS = 5 * 60 * 1000 

    for msg in all_messages:
        ts_ms = msg.get('timestamp_ms', 0)
        dt = datetime.fromtimestamp(ts_ms / 1000.0)
        curr_date = dt.strftime('%Y-%m-%d (%A)')
        curr_time = dt.strftime('%H:%M')
        
        if curr_date != last_date:
            cleaned_output.append(f"\n=== DATE: {curr_date} ===")
            last_date = curr_date
        elif (ts_ms - last_timestamp) > GAP_THRESHOLD_MS:
            gap_dur = (ts_ms - last_timestamp) / 1000 / 3600
            cleaned_output.append(f"\n--- TIME GAP: {gap_dur:.1f} hours ---")

        sender_raw = fix_encoding(msg.get('sender_name', 'Unknown'))
        sender_display = f"[{'YOU' if sender_raw.lower() == user_name.lower() else 'CONTACT'}] {sender_raw}" if self_aware_input == 'y' else sender_raw
        
        raw_content = fix_encoding(msg.get('content', ""))
        
        # Behavioral Flags
        is_unsent = msg.get('is_unsent', False) or "unsent a message" in raw_content.lower()
        is_geoblocked = msg.get('is_geoblocked_for_viewer', False)
        is_sticker = msg.get('sticker') is not None
        is_voice = msg.get('audio_files') is not None
        is_sys_msg = any(p in raw_content for p in ["sent an attachment.", "Liked a message", "Reacted "])

        if is_unsent: content = "[MESSAGE_UNSENT_BY_USER]"
        elif is_geoblocked: content = "[CONTENT_GEOBLOCKED_FOR_RECIPIENT]"
        elif is_sticker: content = "[SENT_A_STICKER]"
        elif is_voice: content = "[VOICE_NOTE_SENT]"
        elif is_sys_msg: content = ""
        else: content = raw_content

        if msg.get('call_duration') is not None:
            content = f"[CALL_LOG: {format_duration(msg['call_duration'])}]"

        # Metadata Strategies
        share_data = msg.get('share', {})
        share_block = ""
        if share_data:
            link = clean_url(share_data.get('link', ''))
            caption = fix_encoding(share_data.get('share_text', ''))
            s_label = "SHARED_LINK"
            if "/stories/" in link: s_label = "STORY_CONTEXT"
            elif "giphy.com" in link:
                slug = link.split('/')[-1].replace('-', ' ').split(' ')[0] if '/' in link else "visual"
                s_label = f"GIF_SENT (Theme: {slug})"

            if meta_choice == '1': # Full
                share_block = f"\n    └─ [{s_label}]: {link}"
                if caption: share_block += f"\n    └─ [CAPTION]: {caption}"
            elif meta_choice == '2': # Optimized
                short_cap = clean_caption(caption)
                if len(short_cap) > 130: short_cap = short_cap[:127] + "..."
                share_block = f"\n    └─ [{s_label}]: {link}"
                if short_cap: share_block += f"\n    └─ [CAPTION_DIGEST]: {short_cap}"
            elif meta_choice == '3': # Minimal
                share_block = f"\n    └─ [{s_label}]: {link}"
            else: # None
                content = f"[{s_label}] {content}".strip()

        if msg.get('photos'): content = f"[MEDIA: Photo] {content}".strip()
        if msg.get('is_edited'): content += " (EDITED)"
        
        reply_data = msg.get('reply_to_source')
        reply_context = ""
        if reply_data:
            r_sender = fix_encoding(reply_data.get('sender_name', 'Unknown'))
            r_content = fix_encoding(reply_data.get('content', '[Media]'))
            reply_context = f"(Reply to {r_sender}: \"{r_content}\") ↳ "

        reactions = msg.get('reactions', [])
        reaction_str = f" [Reactions: {', '.join([f'{fix_encoding(r.get('reaction'))} by {fix_encoding(r.get('actor'))}' for r in reactions])}]" if reactions else ""

        # Conversational Grouping
        if sender_raw == last_sender and (ts_ms - last_timestamp) < GROUPING_THRESHOLD_MS:
            header = "  ↳ "
        else:
            header = f"\n[{curr_time}] {sender_display}: "
        
        if content or share_block:
            cleaned_output.append(f"{header}{reply_context}{content}{reaction_str}{share_block}")
            last_sender = sender_raw
            last_timestamp = ts_ms

    output_filename = f"instascribe_{folder_id_name}.txt"
    final_dir = global_output_path if global_output_path else input_folder
    final_path = os.path.join(final_dir, output_filename)

    with open(final_path, 'w', encoding='utf-8') as f:
        f.write(f"SYSTEM: INSTASCRIBE DM DATASET\n")
        f.write(f"GENERATED_ON: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"FOLDER_SOURCE: {folder_id_name}\n")
        f.write(f"OWNER_IDENTITY: {user_name if user_name else 'Not Specified'}\n")
        f.write(f"PARTICIPANTS: {', '.join(conv['participants'])}\n")
        f.write(f"METADATA_STRATEGY: {meta_labels.get(meta_choice, 'Optimized')}\n")
        f.write("=" * 60 + "\n")
        f.write("\n".join(cleaned_output))
    return final_path

def main():
    print("\n" + "="*50)
    print("   INSTASCRIBE: LLM DATASET OPTIMIZER")
    print("="*50)
    root_path = input("\n1. Paste the path to your 'messages' or 'inbox' folder: ").strip().strip('"').strip("'")
    if not os.path.isdir(root_path):
        print("Error: Invalid path."); return
    conversations = find_conversations(root_path)
    if not conversations:
        print("No valid conversations found."); return
    print(f"\nFound {len(conversations)} conversations.")

    print("\n--- SELECTION ---\n [A] Process ALL\n [S] Select specific")
    choice = input("Choice (A/S): ").lower().strip()
    to_process = conversations if choice == 'a' else []
    if choice == 's':
        print("\nAvailable Conversations:")
        for i, conv in enumerate(conversations, 1):
            print(f" [{i}] {conv['title']} ({conv['folder_id']})")
        idx = input("\nEnter number(s) (e.g. '1,3'): ")
        try:
            to_process = [conversations[int(x.strip())-1] for x in idx.split(',')]
        except:
            print("Invalid selection."); return

    print("\n--- GLOBAL SETTINGS ---")
    self_aware_input = input("Enable Self-Awareness [YOU] labeling? (y/n): ").lower().strip()
    user_name = input("Enter YOUR full name: ").strip() if self_aware_input == 'y' else ""
    print("\nMetadata Density: [1] Full, [2] Optimized, [3] Minimal, [4] None")
    meta_choice = input("Select (1-4): ").strip()
    meta_labels = {"1": "Full", "2": "Optimized", "3": "Minimal", "4": "None"}

    print("\n--- OUTPUT SELECTION ---")
    output_path_input = input("Target folder path (ENTER for default): ").strip().strip('"').strip("'")
    global_output_path = os.path.normpath(output_path_input) if output_path_input else None
    if global_output_path and not os.path.exists(global_output_path): os.makedirs(global_output_path)

    print(f"\nProcessing {len(to_process)} conversations...")
    for conv in to_process:
        saved_path = process_single_conversation(conv, user_name, self_aware_input, meta_choice, meta_labels, global_output_path)
        print(f" ✓ Saved: {conv['title']} -> {os.path.basename(saved_path)}")
    print("\nAll tasks completed successfully.\n")

if __name__ == "__main__":
    main()
