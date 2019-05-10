FROM alpine:3.6

ENV RUNTIME_PACKAGES ca-certificates python3 libxslt libxml2 libssl1.0
ENV BUILD_PACKAGES build-base libxslt-dev libxml2-dev libffi-dev python3-dev openssl-dev

WORKDIR /app

RUN apk add --no-cache $RUNTIME_PACKAGES && \
    update-ca-certificates

COPY . .

RUN apk --no-cache add --virtual build-dependencies $BUILD_PACKAGES && \
    pip3 --no-cache-dir install -r requirements.txt && \
    apk del build-dependencies

ENTRYPOINT ["scrapy"]