FROM python:3.14-alpine3.23

COPY --from=ghcr.io/astral-sh/uv:0.11.21@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 /uv /bin/

COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY src/ src/
COPY README.md README.md
COPY LICENSE LICENSE
RUN uv sync --frozen --no-default-groups --no-editable

RUN adduser --disabled-password hermes
USER hermes

CMD [ "uv", "run", "--no-sync", "-m", "hermes" ]
