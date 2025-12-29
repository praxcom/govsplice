# Use Ubuntu 22.04 (Jammy)
FROM ubuntu:22.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    bzip2 \
    ca-certificates \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Miniconda
ENV CONDA_DIR=/opt/conda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p $CONDA_DIR && \
    rm /tmp/miniconda.sh

# Add conda to PATH
ENV PATH=$CONDA_DIR/bin:$PATH

# Copy the directory
COPY . .

# Accept conda terms of service
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Create conda environment
RUN conda env create -f environment.yml && \
    conda clean -afy

ENV CONDA_DEFAULT_ENV=govsplice
ENV PATH=$CONDA_DIR/envs/govsplice/bin:$PATH

# Open socket
EXPOSE 80

RUN chmod +x init.sh
CMD ["init.sh"]