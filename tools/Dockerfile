
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

# 5.2. Unpack Data (Inject into Default Stage Root)
# Config defaults stage_root to $HOME/stage/$PROJECT_NAME (i.e., /root/stage/app)
# zip_data.py wraps everything in a 'data' folder, so we must unpack and move it up.
RUN mkdir -p /root/stage/app
COPY data.zip /root/stage/app/data.zip
RUN unzip /root/stage/app/data.zip -d /root/stage/app && \
    rm /root/stage/app/data.zip && \
    # Move contents of 'data' (warehouse, hero_profiles, etc.) to stage root
    mv /root/stage/app/data/* /root/stage/app/ && \
    rmdir /root/stage/app/data

# 6. Final Install / Verification
RUN bash package_py.sh

# 7. Setup Runtime
COPY tools/docker_entrypoint.sh /app/run.sh
RUN chmod +x /app/run.sh

EXPOSE 8000
CMD ["/bin/bash", "/app/run.sh"]
