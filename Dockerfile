FROM python
RUN apt-get update && apt-get install -y \
    youtube-dl \
    && ln -s /usr/bin/yt-dlp /usr/local/bin/youtube-dl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt
COPY video.py /video.py
VOLUME /downloads
WORKDIR /downloads
ENTRYPOINT ["python"]
CMD ["/video.py"]
