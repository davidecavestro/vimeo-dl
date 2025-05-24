# vimeo-dl

A container image based on [Javi3rV script](https://gist.github.com/alexeygrigorev/a1bc540925054b71e1a7268e50ad55cd?permalink_comment_id=5279414#gistcomment-5279414) to download segmented videos from vimeo.<br>
It supports _playlist.json_ and _master.json_ urls.


## Example usage

### From docker CLI

```bash
docker run \
  -e 'SRC_URL=https://...' \
  -e 'OUT_FILE=/downloads/video.mp4' \
  -v $(pwd)/out:/downloads \
  --rm -it davidecavestro/vimeo-dl
```

### From docker compose

```yaml
version: "3"

services:
  downloader:
    build:
      context: .
    volumes:
    - ./out:/downloads
    environment:
    - SRC_URL=${SRC_URL}
    - OUT_FILE=${OUT_FILE}
    - MAX_WORKERS=${MAX_WORKERS}
```
passing the url from `.env` file
```.env
SRC_URL=https://...
OUT_FILE=/downloads/video.mp4
MAX_WORKERS=5
```


## Image project home

https://github.com/davidecavestro/vimeo-dl


## Disclaimer

This software is released just for educational purposes.
**Please do not use it for illegal activities.**

## Credits

Entirely based on [alexeygrigorev](https://github.com/alexeygrigorev)'s [vimeo-download.py gist](https://gist.github.com/alexeygrigorev/a1bc540925054b71e1a7268e50ad55cd) and refining comments, just with some minor tweaks.
