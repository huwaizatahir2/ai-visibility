FROM docker.io/postgres:18

# Postgres 18's image moved the default PGDATA to /var/lib/postgresql/18/docker.
# Pin it back to the path our compose volumes mount, so existing volume layout
# (and backups) keep working across the 16 -> 18 bump.
ENV PGDATA=/var/lib/postgresql/data

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
