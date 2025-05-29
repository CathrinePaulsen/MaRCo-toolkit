FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# Install java17, jython
RUN apt-get update && apt-get install -y \
	wget \
	openjdk-17-jdk \
	jython \
	software-properties-common \
	git 

# Install python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa -y && apt-get update && \
    apt-get install -y python3.11 \
    python3-pip

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --config python3

# Install Maven 3.9.6
RUN wget https://downloads.apache.org/maven/maven-3/3.9.6/binaries/apache-maven-3.9.6-bin.tar.gz &&\
	tar -xzvf apache-maven-3.9.6-bin.tar.gz -C /opt &&\
	ln -s /opt/apache-maven-3.9.6 /opt/maven &&\
	ln -s /opt/maven/bin/mvn /usr/bin/mvn &&\
	rm apache-maven-3.9.6-bin.tar.gz
ENV MAVEN_HOME=/opt/maven

COPY . marco
COPY settings.xml $MAVEN_HOME/conf/settings.xml
WORKDIR marco

RUN 	pip install -e core &&\
	pip install -e server &&\
	pip install -e client &&\
	pip install -e rq &&\
	pip install -e rq6
