FROM node:alpine

RUN apk add --no-cache tini git && \
    yarn global add git-http-server && \
    adduser -D -g git git && \
    mkdir /repos && \
    chown git:git /repos

ADD entrypoint.sh /
USER git
WORKDIR /repos

CMD tini -- /entrypoint.sh
