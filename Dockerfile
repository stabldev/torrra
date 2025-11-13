# stage 1: builder
FROM python:3.13-slim AS builder

WORKDIR /app

# install uv
RUN pip install --no-cache-dir uv

# copy dependency definitions
COPY requirements.txt pyproject.toml README.md ./

# copy source code
COPY src ./src

# install dependencies using uv
RUN uv pip install --system --no-cache-dir -r requirements.txt

# stage 2: final image
FROM python:3.13-alpine

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

# create a non-root user and group
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# copy installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# copy the application source and executable
COPY --from=builder --chown=appuser:appgroup /app/src ./src
COPY --from=builder /usr/local/bin/torrra /usr/local/bin/torrra

# switch to the non-root user
USER appuser

# set the entrypoint
ENTRYPOINT ["torrra"]
