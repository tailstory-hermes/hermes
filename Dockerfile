FROM python:3.14-slim@sha256:fb83750094b46fd6b8adaa80f66e2302ecbe45d513f6cece637a841e1025b4ca

COPY --from=ghcr.io/astral-sh/uv:0.9.26@sha256:9a23023be68b2ed09750ae636228e903a54a05ea56ed03a934d00fe9fbeded4b /uv /bin/

COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY src/ src/
COPY README.md README.md
COPY LICENSE LICENSE
RUN uv sync --frozen --no-default-groups --no-editable

RUN adduser --disabled-password hermes
USER hermes

CMD [ "uv", "run", "--no-sync", "-m", "hermes" ]
