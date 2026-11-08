FROM ubuntu:24.04

WORKDIR /pylabot

COPY requirements.txt *.py *.json ./

RUN apt update && \
    apt install -y python3-pip && \
	pip install -r requirements.txt uwsgi --no-cache-dir --break-system-packages && \
	rm requirements.txt

#ENTRYPOINT
CMD uwsgi -w pylabot:app --http :5000
