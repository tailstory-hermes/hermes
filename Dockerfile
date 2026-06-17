FROM python:3.14-alpine3.23

COPY --from=ghcr.io/astral-sh/uv:0.11.21-alpine3.23@sha256:373dfd5043b1ceead32ef953f8970f3c694b6ccc8f9b2bb9fc21bf6cd665bfa2 /uv /bin/

COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY src/ src/
COPY README.md README.md
COPY LICENSE LICENSE
RUN uv sync --frozen --no-default-groups --no-editable

RUN adduser --disabled-password hermes
USER hermes

CMD [ "uv", "run", "--no-sync", "-m", "hermes" ]
