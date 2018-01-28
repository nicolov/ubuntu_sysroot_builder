FROM ubuntu:trusty

ENV DEBIAN_FRONTEND noninteractive

# Set up the compiler
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        clang-3.8

# Make sure libpng is not installed
RUN apt-get remove -y --no-install-recommends \
    libpng12-0
