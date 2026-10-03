FROM node:19-bullseye
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends g++-arm-linux-gnueabihf \
 && rm -rf /var/lib/apt/lists/*
