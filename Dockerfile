ARG BUILD_VERSION

FROM ubuntu:20.04 AS base
ARG DEBIAN_FRONTEND=noninteractive
ARG OTTER_SERVICE_STDALONE_VERSION

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y software-properties-common && \
    apt-get update && \
    add-apt-repository -y ppa:longsleep/golang-backports

RUN apt-get install -y python3 && \
    apt-get install -y python3-pip && \
    apt-get install -y curl && \
    apt-get install -y golang

# install golang to support sops(python-sops does nto work with GCP KMS)
RUN echo 'export PATH=$PATH:/root/go/bin' >> /root/.bashrc && \
    go install go.mozilla.org/sops/v3/cmd/sops@v3.7.3

RUN mkdir -p /etc/otter-service-stdalone
ADD ./requirements.txt /etc/otter-service-stdalone/requirements.txt
RUN --mount=type=cache,target=~/.cache/pip python3 -m pip install -r /etc/otter-service-stdalone/requirements.txt

# install docker cli
ENV DOCKER_VERSION 5:20.10.17~3-0~ubuntu-focal
RUN apt-get update
RUN apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update
RUN apt-get -y install docker-ce-cli=${DOCKER_VERSION}
RUN apt-get -y install unzip
RUN apt install -y python3.8-venv

ADD ./deployment/autograder.zip /etc/otter-service-stdalone
ADD ./deployment/notebooks.zip /etc/otter-service-stdalone
ADD ./deployment/autograder-3.3.0.zip /etc/otter-service-stdalone
ADD ./deployment/notebooks-3.3.0.zip /etc/otter-service-stdalone
RUN unzip /etc/otter-service-stdalone/notebooks.zip -d /etc/otter-service-stdalone/notebooks/
RUN unzip /etc/otter-service-stdalone/notebooks-3.3.0.zip -d /etc/otter-service-stdalone/notebooks-3.3.0/

COPY ./docker-pull-otter.sh /etc/otter-service-stdalone
RUN chmod 755 /etc/otter-service-stdalone/docker-pull-otter.sh

WORKDIR /opt
EXPOSE 80

FROM base as image-local
COPY ./dist/otter_service_stdalone-${OTTER_SERVICE_STDALONE_VERSION}.tar.gz /opt/otter-service-stdalone/
RUN python3 -m pip install /opt/otter-service-stdalone/otter_service_stdalone-${OTTER_SERVICE_STDALONE_VERSION}.tar.gz
ENTRYPOINT ["otter_service_stdalone"]

FROM base as image-cloud
RUN python3 -m pip install otter-service-stdalone
ENTRYPOINT ["otter_service_stdalone"]

