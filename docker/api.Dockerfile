FROM ghcr.io/astral-sh/uv:0.10.12 AS uv

FROM python:3.12-slim

WORKDIR /app

ARG UV_EXTRAS=""
ARG INSTALL_PLAYWRIGHT="false"

COPY --from=uv /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN set -eu; \
        extra_args=""; \
        if [ -n "$UV_EXTRAS" ]; then \
            old_ifs="$IFS"; \
            IFS=','; \
            for extra in $UV_EXTRAS; do \
                if [ -n "$extra" ]; then \
                    extra_args="$extra_args --extra $extra"; \
                fi; \
            done; \
            IFS="$old_ifs"; \
        fi; \
        uv sync --frozen --no-dev --no-install-project $extra_args

ENV VIRTUAL_ENV=/app/.venv
ENV PATH=/app/.venv/bin:$PATH

COPY . .

RUN if [ "$INSTALL_PLAYWRIGHT" = "true" ] && command -v playwright >/dev/null 2>&1; then \
            playwright install chromium --with-deps; \
        fi

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "socialmind.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
