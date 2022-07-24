FROM python:3.9-slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt
COPY . /app
ARG BOT_TOKEN
ENV YOUTUBE_TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
ENTRYPOINT [ "./main.py"]