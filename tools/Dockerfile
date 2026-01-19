
# Base Image: Ubuntu 22.04 LTS
FROM ubuntu:22.04

# Avoid interactive prompts during apt install
ARG DEBIAN_FRONTEND=noninteractive

# 1. System Dependencies
# - python3, pip, venv: Core Python
# - openjdk-17-jdk: Required for Spark 4.0
# - git, curl, tar: Utilities
# - build-essential: For compiling python libs if needed
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-17-jdk \
    git \
    curl \
    tar \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Environment
WORKDIR /app
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# 3. Copy Project
# We expect the build context to be the project root
COPY . /app

# 3.1. Unpack Data (if provided via zip)
# We copy data.zip (prepared by build script) and unzip it
COPY data.zip /app/data.zip
RUN unzip /app/data.zip -d /app && rm /app/data.zip

# 4. Install Project & Dependencies
# We use the existing installer script which handles Spark download and pip install
# We force HOME to /root so it installs Spark to /root/opt
ENV HOME=/root
RUN bash package_py.sh

# 5. Setup Runtime
# Copy the entrypoint script
COPY tools/docker_entrypoint.sh /app/run.sh
RUN chmod +x /app/run.sh

# Expose the server port
EXPOSE 8000

# Start the server
CMD ["/app/run.sh"]
