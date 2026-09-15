FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml setup.py README.md LICENSE ./
COPY solarconflux ./solarconflux
RUN pip install --no-cache-dir .
COPY web ./web
COPY scripts/build_web.py ./scripts/build_web.py
RUN python scripts/build_web.py && useradd --create-home solarconflux && chown -R solarconflux /app
USER solarconflux
ENV PORT=8080
EXPOSE 8080
CMD ["python", "-m", "solarconflux.server", "--host", "0.0.0.0"]
