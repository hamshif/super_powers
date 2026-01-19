
# Base Image: Python 3.11 (Debian Bookworm)
FROM python:3.11-slim

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# 1. System Dependencies
# - default-jdk: Points to stable Java (17 on Bookworm)
# - git, curl, unzip, tar: utilities
# - build-essential: for compiling wheels if needed
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

# 3. Optimization: Spark Layer (Heavy Download)
# We download Spark once here so it's cached.
# URL matches package_py.sh
WORKDIR /root/opt
RUN curl -fLo spark.tgz "https://archive.apache.org/dist/spark/spark-4.0.1/spark-4.0.1-bin-hadoop3.tgz" \
    && tar -xzf spark.tgz \
    && rm spark.tgz
# Note: package_py.sh expects specific dir name, tar extraction provides it.

# 4. Optimization: Python Dependencies (Heavy Wheels)
# We copy only the dependency definition to cache pip installs
WORKDIR /app
COPY super-services/pyproject.toml /app/super-services/pyproject.toml

# We create a dummy source structure so pip can install the package in editable mode
# This installs dependencies (pandas, pyspark, etc.) and caches them.
RUN mkdir -p /app/super-services/src/super && \
    touch /app/super-services/src/super/__init__.py && \
    python -m pip install --upgrade pip setuptools wheel && \
    pip install -e /app/super-services

# 5. Full Project Copy
# This invalidates cache for subsequent steps, but dependencies are already installed.
COPY . /app

# 5.1. Unpack Data (if provided via zip)
COPY data.zip /app/data.zip
RUN unzip /app/data.zip -d /app && rm /app/data.zip

# 6. Final Install / Verification
# package_py.sh will verify Spark exists (it does) and re-run pip install -e (fast, just updates metadata)
RUN bash package_py.sh

# 7. Setup Runtime
COPY tools/docker_entrypoint.sh /app/run.sh
RUN chmod +x /app/run.sh

# Expose the server port
EXPOSE 8000

# Start the server
CMD ["/bin/bash", "/app/run.sh"]
