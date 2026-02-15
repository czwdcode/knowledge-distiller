#!/usr/bin/env python3
import os
import sys
import subprocess
import yt_dlp

PLAYLIST_URL = sys.argv[1] if len(sys.argv) > 1 else input("请输入 B站合集链接: ")
PROXY = ""      # ← 按需修改
COOKIES = ""                # ← 按需修改
OUTPUT_DIR = "./subtitles"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Step 1: 提取所有视频 URL（flat 模式）
print("🔍 正在提取视频地址...")
with yt_dlp.YoutubeDL({'extract_flat': True, 'skip_download': True, 'quiet': True}) as ydl:
    info = ydl.extract_info(PLAYLIST_URL, download=False)
    urls = [entry['url'] for entry in info['entries'] if 'url' in entry]

print(f"✅ 共提取 {len(urls)} 个视频地址")

# Step 2: 逐个调用 yt-dlp 下载字幕
for i, url in enumerate(urls, 1):
    print(f"\n[{i}/{len(urls)}] 正在下载字幕: {url}")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-subs", 
        "--sub-langs", "ai-zh",
        "--output", os.path.join(OUTPUT_DIR, "%(playlist_title)s", "%(title)s.%(ext)s")
    ]
    if PROXY:
        cmd += ["--proxy", PROXY]
    if COOKIES and os.path.isfile(COOKIES):
        cmd += ["--cookies", COOKIES]
    cmd.append(url)

    subprocess.run(cmd)