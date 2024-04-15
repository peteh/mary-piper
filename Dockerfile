FROM python:3.10-bookworm
#VOLUME /storage
RUN mkdir -p /root/.cache && ln -s /storage /root/.cache/huggingface && mkdir -p /root/.local && ln -s /storage /root/.local/share
#RUN apt-get update && apt-get install -y opus-tools vorbis-tools ffmpeg espeak
WORKDIR /app
COPY app/ .
RUN pip3 install -U -r requirements.txt
CMD ["python3", "-u", "server.py"]

ENV SERVER_PORT 59125
EXPOSE 59125/tcp
