
# ==========================================
# Stage 1: Build Frontend (Super Web)
# ==========================================
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# Copy package files first for caching
COPY super-web/package.json super-web/package-lock.json ./
RUN npm ci

# Copy source and build
COPY super-web/ ./
RUN npm run build

# ==========================================
# Stage 2: Backend Runtime
# ==========================================
FROM python:3.11-slim

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# 1. System Dependencies
RUN mkdir -p /usr/share/man/man1 && \
    apt-get update && apt-get install -y \
    default-jdk \
    git \
    curl \
    unzip \
    tar \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Environment
WORKDIR /app
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
ENV HOME=/root
ENV PYTHONUNBUFFERED=1

# 3. Optimization: Spark Layer
WORKDIR /root/opt
RUN curl -fLo spark.tgz "https://archive.apache.org/dist/spark/spark-4.0.1/spark-4.0.1-bin-hadoop3.tgz" \
    && tar -xzf spark.tgz \
    && rm spark.tgz

# 4. Optimization: Python Dependencies
WORKDIR /app
COPY super-services/pyproject.toml /app/super-services/pyproject.toml
RUN mkdir -p /app/super-services/src/super && \
    touch /app/super-services/src/super/__init__.py && \
    python -m pip install --upgrade pip setuptools wheel && \
    pip install -e /app/super-services

# 5. Full Project Copy
COPY . /app

# 5.1 Inject Frontend Build
# Overwrite the static directory with the compiled React app
# (Note: This replaces any 'chat.html' we stuck there)
COPY --from=frontend-builder /app/frontend/dist /app/super-services/src/super/apps/super_power_sage/static

# 5.2. Inject Data (Pre-unzipped in stage)
# process: build_docker.sh unzziped 'data.zip' into 'stage/docker_context/data'
# So we just copy that directory to the expected location.
# Config defaults stage_root to $HOME/stage/$PROJECT_NAME (i.e., /root/stage/app)
RUN mkdir -p /root/stage/app
COPY data /root/stage/app/
# Note: if data.zip contained 'data/', then verify path.
# Assuming build_docker.sh unzipping results in 'stage/docker_context/data/' containing the parquet files.
# If so, COPY data /root/stage/app/ puts them in /root/stage/app/ (files) or /root/stage/app/data/?
# COPY src dest -> If dest ends with /, it's a directory.
# If src is a directory, it copies CONTENTS.
# Wait, Docker COPY behavior: "COPY data /dest/" copies contents of data into /dest/.
# If we want /root/stage/app to CONTAIN 'hero_profiles' etc directly?
# Check previous logic:
# unzip ... -d /root/stage/app
# mv /root/stage/app/data/* /root/stage/app/
# So previously, data.zip had a 'data' folder at root.
# So unzipping to /root/stage/app created /root/stage/app/data.
# Then we moved contents UP.
# So we want the contents of 'data' to be in '/root/stage/app'.
#
# If we have 'stage/docker_context/data' on host.
# COPY data /root/stage/app/ ---> copies 'stage/docker_context/data' CONTENTS into '/root/stage/app/'?
# OR does it copy the directory itself?
# "COPY src dest": If src is dir, "metadata of the directory itself is not copied (the directory name), just its contents".
# So COPY data /root/stage/app/ will put hero_profiles inside /root/stage/app/.
# This matches the desired "mv ... *" state.


# 6. Final Install / Verification
RUN bash package_py.sh

# 7. Setup Runtime
COPY tools/docker_entrypoint.sh /app/run.sh
RUN chmod +x /app/run.sh

EXPOSE 8000
CMD ["/bin/bash", "/app/run.sh"]
