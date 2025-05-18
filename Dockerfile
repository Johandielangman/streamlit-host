FROM python:3.11-slim

# =========== // ENVIRONMENT VARIABLES // ===========

ENV APP_ROOT=/self-hosted-streamlit-apps
ENV ALWAYS_HEALTHY=false

# =========== // ARGS // ===========

ARG DEBIAN_FRONTEND=noninteractive

# =========== // INSTALLATIONS // ===========

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    file \
    git \
    supervisor \
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && \
#     chmod +x /usr/local/bin/cloudflared


# =========== // WORKING DIRECTORY SETUP // ===========

WORKDIR $APP_ROOT
COPY . .
RUN mkdir -p /var/log/supervisor /etc/cloudflared

# COPY cloudflare/ /etc/cloudflared/

# =========== // BUILD SCRIPTS // ===========

RUN python build.py -dH && \
    cp supervisord.conf /etc/supervisor/supervisord.conf && \
    cp nginx.conf /etc/nginx/sites-available/default && \
    ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# =========== // ENTRYPOINT AND HEALTHCHECK // ===========

HEALTHCHECK --interval=5m --timeout=3s --start-period=5s --start-interval=5s --retries=3\
  CMD python healthcheck.py || exit 1

# =========== // EXPOSE PORTS // ===========

EXPOSE 80

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
