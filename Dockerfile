FROM ghcr.io/prefix-dev/pixi:0.31.0 AS build

WORKDIR /app
COPY . .
RUN pixi install --locked
RUN pixi shell-hook -s bash > /shell-hook
RUN echo "#!/bin/bash" > /app/entrypoint.sh
RUN cat /shell-hook >> /app/entrypoint.sh
RUN echo 'exec "$@"' >> /app/entrypoint.sh

FROM ubuntu:24.04 AS production
WORKDIR /app
COPY --from=build /app/.pixi/envs/default /app/.pixi/envs/default
COPY --from=build --chmod=0755 /app/entrypoint.sh /app/entrypoint.sh
COPY ./maaamet-address-query /app/maaamet-address-query

EXPOSE 8000
ENTRYPOINT [ "/app/entrypoint.sh" ]
CMD [ "uvicorn", "maaamet-address-query.main:app", "--host", "0.0.0.0" ]
