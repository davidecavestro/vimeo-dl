import os
import sys
import base64
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm
import ffmpeg


url = os.getenv("SRC_URL") or input('enter [master|playlist].json url: ')
name = os.getenv("OUT_FILE") or input('enter output name: ')
max_workers = min(int(os.getenv("MAX_WORKERS", 5)), 15)

if 'master.json' in url:
    url = url[:url.find('?')] + '?query_string_ranges=1'
    url = url.replace('master.json', 'master.mpd')
    print(url)
    subprocess.run(['youtube-dl', url, '-o', name])
    sys.exit(0)


def download_segment(segment_url, segment_path):
    resp = requests.get(segment_url, stream=True)
    if resp.status_code != 200:
        print('not 200!')
        print(segment_url)
        return
    with open(segment_path, 'wb') as segment_file:
        for chunk in resp:
            segment_file.write(chunk)


def download(what, to, base, max_workers):
    print('saving', what['mime_type'], 'to', to)
    init_segment = base64.b64decode(what['init_segment'])

    segment_urls = [base + segment['url'] for segment in what['segments']]
    segment_paths = [f"segment_{i}.tmp" for i in range(len(segment_urls))]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(executor.map(download_segment, segment_urls,
             segment_paths), total=len(segment_urls)))

    with open(to, 'wb') as file:
        file.write(init_segment)
        for segment_path in segment_paths:
            with open(segment_path, 'rb') as segment_file:
                file.write(segment_file.read())
            os.remove(segment_path)

    print('done')


base_url = url[:url.rfind('/', 0, -26) + 1]
content = requests.get(url).json()

vid_heights = [(i, d['height']) for (i, d) in enumerate(content['video'])]
vid_idx, _ = max(vid_heights, key=lambda _h: _h[1])

audio_quality = [(i, d['bitrate']) for (i, d) in enumerate(content['audio'])]
audio_idx, _ = max(audio_quality, key=lambda _h: _h[1])

video = content['video'][vid_idx]
audio = content['audio'][audio_idx]
base_url = base_url + content['base_url']

video_tmp_file = 'video.mp4'
audio_tmp_file = 'audio.mp4'

download(video, video_tmp_file, base_url + video['base_url'], max_workers)
download(audio, audio_tmp_file, base_url + audio['base_url'], max_workers)


def combine_video_audio(video_file, audio_file, output_file):
    try:
        video_stream = ffmpeg.input(video_file)
        audio_stream = ffmpeg.input(audio_file)

        ffmpeg.output(video_stream, audio_stream, output_file,
                      vcodec='copy', acodec='copy').run(overwrite_output=True)

        print(f"Fragments joined into {output_file}")
    except ffmpeg.Error as e:
        print(f"Cannot join fragments: {e.stderr.decode()}")


combine_video_audio('video.mp4', 'audio.mp4', name)

os.remove(video_tmp_file)
os.remove(audio_tmp_file)
