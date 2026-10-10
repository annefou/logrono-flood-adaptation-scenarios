FROM ghcr.io/prefix-dev/pixi:0.68.1

LABEL org.opencontainers.image.source="https://github.com/annefou/logrono-flood-adaptation-scenarios"
LABEL org.opencontainers.image.description="Replication study container for logrono-flood-adaptation-scenarios"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install the pinned environment first (separate from source copy so the lock
# layer is cached across source-only edits).
# git: pixi installs building-climate-risk from its GitHub tag (pixi.toml
# [pypi-dependencies]); the pixi base image ships without git.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY pixi.toml pixi.lock /app/
RUN pixi install --locked

COPY . /app

# The Climate DT retrieval (scripts/retrieve.py) needs a DestinE Polytope key:
#   docker run -v ~/.polytopeapirc:/root/.polytopeapirc logrono-flood-adaptation-scenarios
# See scripts/climatedt.py for the credential setup.

CMD ["pixi", "run", "snakemake", "--cores", "1"]
