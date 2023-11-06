FROM debian:bookworm-slim
RUN apt update && apt install -y gpg apache2 python3-websockets python3-argon2 python3-aiohttp python3-aiohttp-session wget supervisor && \
  wget https://github.com/AllStarLink/Allmon3/releases/download/rel_t_1_0_1/allmon3_1.0.1-1_all.deb && \
  apt install -y ./allmon3_1.0.1-1_all.deb && \
  apt-get clean && \
  rm ./allmon3_1.0.1-1_all.deb
COPY allmon3-web.sh .
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
EXPOSE 80
CMD ["/usr/bin/supervisord"]
