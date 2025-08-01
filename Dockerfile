FROM python:3.13-alpine

WORKDIR /code

RUN apk add --no-cache curl

ENV TORRRA_VERSION=1.2.4
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

RUN curl -L https://github.com/stabldev/torrra/archive/refs/tags/v${TORRRA_VERSION}.tar.gz | tar -xz

WORKDIR /code/torrra-${TORRRA_VERSION}

RUN pip install .

ENTRYPOINT ["torrra"]
