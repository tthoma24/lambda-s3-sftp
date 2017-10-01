FROM amazonlinux:latest
LABEL maintainer "YunoJuno <code@yunojuno.com>"

# install pre-requisites
RUN yum -y groupinstall development && \
    yum -y install zlib-devel openssl-devel wget

# Need to install OpenSSL also to avoid SSL errors with pip
RUN wget https://github.com/openssl/openssl/archive/OpenSSL_1_0_2l.tar.gz && \
    tar -zxvf OpenSSL_1_0_2l.tar.gz && \
    cd openssl-OpenSSL_1_0_2l/ && \

    ./config shared && \
    make && \
    make install && \
    export LD_LIBRARY_PATH=/usr/local/ssl/lib/ && \

    cd .. && \
    rm OpenSSL_1_0_2l.tar.gz && \
    rm -rf openssl-OpenSSL_1_0_2l/

# Install Python 3.6
RUN wget https://www.python.org/ftp/python/3.6.0/Python-3.6.0.tar.xz && \
    tar xJf Python-3.6.0.tar.xz && \
    cd Python-3.6.0 && \

    ./configure && \
    make && \
    make install && \

    cd .. && \
    rm Python-3.6.0.tar.xz && \
    rm -rf Python-3.6.0 && \

    pip3 install pip-tools virtualenv

VOLUME ["/lambda"]
WORKDIR "/lambda"
ENTRYPOINT ["make"]
CMD ["package"]