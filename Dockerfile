FROM python:3.10-bookworm
#VOLUME /storage
RUN mkdir -p /cache_voices/ && mkdir -p /custom_voices/
#RUN apt-get update && apt-get install -y opus-tools vorbis-tools ffmpeg espeak
WORKDIR /app
COPY app/ .
RUN pip3 install -U -r requirements.txt
CMD ["python3", "-u", "server.py", "--cache-dir", "/cache_voices/", "--custom-voice-dir", "/custom_voices/" ]

ENV SERVER_PORT 59125
EXPOSE 59125/tcp
