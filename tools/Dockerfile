
# Base Image: Python 3.11 (Debian Bookworm)
# Ubuntu 22.04 only has Python 3.10, but we need 3.11+ for some deps (e.g. networkx>=3.5)
FROM python:3.11-slim

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# 1. System Dependencies
# - Fix for slim images: Create man directory
RUN mkdir -p /usr/share/man/man1

# - default-jdk: Points to stable Java (17 on Bookworm)
# - git, curl, unzip, tar: utilities
# - build-essential: for compiling wheels if needed
RUN apt-get update && apt-get install -y \
    default-jdk \
    git \
    curl \
    unzip \
    tar \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Environment
WORKDIR /app
# Standard path for OpenJDK 17 on Debian
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# 3. Copy Project
COPY . /app

# 3.1. Unpack Data (if provided via zip)
# We copy data.zip (prepared by build script) and unzip it
COPY data.zip /app/data.zip
RUN unzip /app/data.zip -d /app && rm /app/data.zip

# 4. Install Project & Dependencies
# We use the existing installer script which handles Spark download and pip install
# We force HOME to /root so it installs Spark to /root/opt
ENV HOME=/root

# Upgrade build tools to support PEP 660 (editable installs)
RUN python -m pip install --upgrade pip setuptools wheel

# Install
RUN bash package_py.sh

# 5. Setup Runtime
# Copy the entrypoint script
COPY tools/docker_entrypoint.sh /app/run.sh
RUN chmod +x /app/run.sh

# Expose the server port
EXPOSE 8000

# Start the server
CMD ["/app/run.sh"]
