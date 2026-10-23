# syntax=docker/dockerfile:1
#
# Imagen del Agente 1 (#143, ADR 0013). Dos etapas útiles:
#
# - `test`: la suite y el linter corren adentro, con el mismo Python que el
#   runtime. El CI la construye en cada PR y push (`--target test`).
# - `runtime`: sólo el código controlado, sin tests ni dependencias de terceros
#   (el proyecto declara `dependencies = []`), con un usuario no root. Es la
#   imagen que se publica en ghcr.io al cortar una versión.
#
# Nunca entra a la imagen: la clave de la cuenta de servicio, el env file, el
# estado ni los modelos. Todo eso se monta en tiempo de ejecución (compose).
#
# La base se fija por digest para que la misma versión construya la misma
# imagen. Se actualiza a propósito, como cualquier cambio controlado.

ARG PYTHON_IMAGE=python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.10

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/p100/Implementacion/Agente1/src \
    TZ=America/Argentina/Buenos_Aires
WORKDIR /srv/p100/Implementacion/Agente1

FROM base AS test
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv run --frozen ruff check . && uv run --frozen pytest -q -p no:cacheprovider

FROM base AS runtime
ARG VERSION=dev
ARG REVISION=desconocida
LABEL org.opencontainers.image.source="https://github.com/SpendIce/Proyecto-Final" \
      org.opencontainers.image.title="agente1" \
      org.opencontainers.image.description="Agente 1 (Extensión Bot) del P100: borradores con validación humana" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"
RUN useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin agente1
COPY pyproject.toml uv.lock manifest-version.json Dockerfile ./
COPY src ./src
COPY scripts ./scripts
COPY migrations ./migrations
COPY systemd ./systemd
COPY docker ./docker
COPY data ./data
USER 10001
ENTRYPOINT ["python", "/srv/p100/Implementacion/Agente1/scripts/contenedor_entrypoint.py"]
CMD ["consola"]
