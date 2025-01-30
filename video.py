import importlib.metadata
import subprocess
import sys

required = {'requests', 'tqdm', 'moviepy'}
installed = {pkg.metadata['Name'] for pkg in importlib.metadata.distributions()}
missing = required - installed

if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])


import os
import base64
import requests
from shutil import which
from tqdm import tqdm
from random import choice
from string import ascii_lowercase
from concurrent.futures import ThreadPoolExecutor

has_ffmpeg = False
moviepy_deprecated = False
has_youtube_dl = False
has_yt_dlp = False

if which('ffmpeg') is not None:
    has_ffmpeg = True

if which('youtube-dl') is not None:
    has_youtube_dl = True

if which('yt-dlp') is not None:
    has_yt_dlp = True

if not has_ffmpeg:
    try:
        from moviepy.editor import *  # before 2.0, deprecated
        moviepy_deprecated = True
    except ImportError:
        from moviepy import *  # after 2.0

url = input('enter [master|playlist].json url: ')
name = input('enter output name: ')

if 'master.json' in url:
    url = url[:url.find('?')] + '?query_string_ranges=1'
    url = url.replace('master.json', 'master.mpd')
    print(url)

    if has_youtube_dl:
        subprocess.run(['youtube-dl', url, '-o', name])
        sys.exit(0)

    if has_yt_dlp:
        subprocess.run(['yt-dlp', url, '-o', name])
        sys.exit(0)

    print('you should have youtube-dl or yt-dlp in your PATH to download master.json like links')
    sys.exit(1)


def download_segment(segment_url, segment_path):
    resp = requests.get(segment_url, stream=True)
    if resp.status_code != 200:
        print('not 200!')
        print(segment_url)
        return
    with open(segment_path, 'wb') as segment_file:
        for chunk in resp:
            segment_file.write(chunk)


def download(what, to, base):
    print('saving', what['mime_type'], 'to', to)
    init_segment = base64.b64decode(what['init_segment'])

    # suffix for support multiple downloads in same folder
    segment_suffix = ''.join(choice(ascii_lowercase) for i in range(20)) + '_'

    segment_urls = [base + segment['url'] for segment in what['segments']]
    segment_paths = [f"segment_{i}_" + segment_suffix + ".tmp" for i in range(len(segment_urls))]

    with ThreadPoolExecutor(max_workers=15) as executor:
        list(tqdm(executor.map(download_segment, segment_urls, segment_paths), total=len(segment_urls)))

    with open(to, 'wb') as file:
        file.write(init_segment)
        for segment_path in segment_paths:
            with open(segment_path, 'rb') as segment_file:
                file.write(segment_file.read())
            os.remove(segment_path)

    print('done')


name += '.mp4'
base_url = url[:url.rfind('/', 0, -26) + 1]
response = requests.get(url)
if response.status_code >= 400:
    print('error: cant get url content, test your link in browser, code=', response.status_code, '\ncontent:\n', response.content)
    sys.exit(1)

content = response.json()

vid_heights = [(i, d['height']) for (i, d) in enumerate(content['video'])]
vid_idx, _ = max(vid_heights, key=lambda _h: _h[1])

audio_present = True
if not content['audio']:
    audio_present = False

audio_quality = None
audio_idx = None
if audio_present:
    audio_quality = [(i, d['bitrate']) for (i, d) in enumerate(content['audio'])]
    audio_idx, _ = max(audio_quality, key=lambda _h: _h[1])

base_url = base_url + content['base_url']

# prefix for support multiple downloads in same folder
files_prefix = ''.join(choice(ascii_lowercase) for i in range(20)) + '_'

video_tmp_file = files_prefix + 'video.mp4'
video = content['video'][vid_idx]
download(video, video_tmp_file, base_url + video['base_url'])

audio_tmp_file = None
if audio_present:
    audio_tmp_file = files_prefix + 'audio.mp4'
    audio = content['audio'][audio_idx]
    download(audio, audio_tmp_file, base_url + audio['base_url'])

if not audio_present:
    os.rename(video_tmp_file, name)
    sys.exit(0)

if has_ffmpeg:
    subprocess.run(['ffmpeg', '-i', video_tmp_file, '-i', audio_tmp_file, '-c:v', 'copy', '-c:a', 'copy', name])
    os.remove(video_tmp_file)
    os.remove(audio_tmp_file)
    sys.exit(0)

video_clip = VideoFileClip(video_tmp_file)
audio_clip = AudioFileClip(audio_tmp_file)

final_clip = None
if moviepy_deprecated:
    final_clip = video_clip.set_audio(audio_clip)
else:
    final_clip = video_clip.with_audio(audio_clip)

final_clip.write_videofile(name)

os.remove(video_tmp_file)
os.remove(audio_tmp_file)
