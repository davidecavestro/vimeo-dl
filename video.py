#!/usr/bin/env python3
"""vimeo-dl: Download segmented videos from Vimeo CDN."""

import argparse
import base64
import os
import subprocess
import sys
from random import choice
from shutil import which
from string import ascii_lowercase
from concurrent.futures import ThreadPoolExecutor

__version__ = '0.3.0'

# Lazy-loaded after ensure_deps()
requests = None
tqdm = None


def parse_args():
    parser = argparse.ArgumentParser(
        prog='vimeo-dl',
        description='Download segmented videos from Vimeo CDN.',
        epilog='''examples:
  vimeo-dl 'https://...playlist.json?...' -o my_video
  vimeo-dl 'https://...master.json?...' -o my_video
  vimeo-dl 'https://...playlist.json?...' -o /path/to/my_video -w 10

NOTE: Always quote the URL to prevent shell interpretation of special
characters (?, &, =, etc). Use single quotes to be safe.''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        'url', nargs='?', default=None,
        help="playlist.json or master.json URL (QUOTE THIS -- it contains &, =, etc)",
    )
    parser.add_argument(
        '-o', '--output', default=None, metavar='NAME',
        help='output filename without .mp4 extension (can include path)',
    )
    parser.add_argument(
        '-w', '--workers', type=int, default=None, metavar='N',
        help='parallel download threads (default: 5, max: 15)',
    )
    parser.add_argument(
        '-v', '--version', action='version', version=f'%(prog)s {__version__}',
    )

    args = parser.parse_args()

    # Resolve values: CLI args > env vars > interactive prompt
    args.url = args.url or os.getenv('SRC_URL') or input('enter [master|playlist].json url: ')
    args.output = args.output or os.getenv('OUT_FILE') or input('enter output name: ')
    args.workers = min(args.workers or int(os.getenv('MAX_WORKERS', 5)), 15)

    return args


def ensure_deps():
    import importlib.metadata
    required = {'requests', 'tqdm', 'moviepy'}
    installed = {pkg.metadata['Name'] for pkg in importlib.metadata.distributions()}
    missing = required - installed
    if missing:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])


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

    # suffix for support multiple downloads in same folder
    segment_suffix = ''.join(choice(ascii_lowercase) for i in range(20)) + '_'

    segment_urls = [base + segment['url'] for segment in what['segments']]
    segment_paths = [f"segment_{i}_" + segment_suffix + ".tmp" for i in range(len(segment_urls))]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(executor.map(download_segment, segment_urls, segment_paths), total=len(segment_urls)))

    with open(to, 'wb') as file:
        file.write(init_segment)
        for segment_path in segment_paths:
            with open(segment_path, 'rb') as segment_file:
                file.write(segment_file.read())
            os.remove(segment_path)

    print('done')


def main():
    args = parse_args()
    ensure_deps()

    global requests, tqdm
    import requests as _requests
    from tqdm import tqdm as _tqdm
    requests = _requests
    tqdm = _tqdm

    has_ffmpeg = which('ffmpeg') is not None
    has_youtube_dl = which('youtube-dl') is not None
    has_yt_dlp = which('yt-dlp') is not None

    moviepy_deprecated = False
    if not has_ffmpeg:
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip  # before 2.0, deprecated
            moviepy_deprecated = True
        except ImportError:
            from moviepy import VideoFileClip, AudioFileClip  # after 2.0

    url = args.url
    name = args.output
    max_workers = args.workers

    if 'deps://install' == url:
        print('exiting afteter installing dependencies')
        sys.exit(0)

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

    audio_idx = None
    if audio_present:
        audio_quality = [(i, d['bitrate']) for (i, d) in enumerate(content['audio'])]
        audio_idx, _ = max(audio_quality, key=lambda _h: _h[1])

    base_url = base_url + content['base_url']

    # prefix for support multiple downloads in same folder
    files_prefix = ''.join(choice(ascii_lowercase) for i in range(20)) + '_'

    video_tmp_file = files_prefix + 'video.mp4'
    video = content['video'][vid_idx]
    download(video, video_tmp_file, base_url + video['base_url'], max_workers)

    audio_tmp_file = None
    if audio_present:
        audio_tmp_file = files_prefix + 'audio.mp4'
        audio = content['audio'][audio_idx]
        download(audio, audio_tmp_file, base_url + audio['base_url'], max_workers)

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

    if moviepy_deprecated:
        final_clip = video_clip.set_audio(audio_clip)
    else:
        final_clip = video_clip.with_audio(audio_clip)

    final_clip.write_videofile(name)

    os.remove(video_tmp_file)
    os.remove(audio_tmp_file)


if __name__ == '__main__':
    main()
