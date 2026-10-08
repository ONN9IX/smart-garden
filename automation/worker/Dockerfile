# Retired executor: intentionally no Codex CLI or authentication cache.
# Isolated private automation worker. No external exposed ports or Docker socket.
FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 git ca-certificates util-linux && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 10001 agent && useradd -m -u 10001 -g 10001 -s /usr/sbin/nologin agent && \
    mkdir -p /workspace && \
    chown -R 10001:10001 /home/agent
COPY policy.py worker.py /opt/worker/
COPY github-askpass /usr/local/bin/github-askpass
RUN chmod 0755 /usr/local/bin/github-askpass && \
    chmod 0755 /opt/worker && chmod 0644 /opt/worker/*.py
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /opt/worker
EXPOSE 8080
CMD ["python3", "-B", "worker.py"]
