FROM python
RUN apt-get update && apt-get install -y \
    youtube-dl \
    && ln -s /usr/bin/yt-dlp /usr/local/bin/youtube-dl \
    && rm -rf /var/lib/apt/lists/*
VOLUME /downloads
WORKDIR /downloads
COPY video.py /video.py
RUN export SRC_URL=deps://install; \
    export OUT_FILE=/downloads/video.mp4; \
    python /video.py

ENTRYPOINT ["python"]
CMD ["/video.py"]
