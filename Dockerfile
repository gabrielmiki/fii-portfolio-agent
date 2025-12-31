# Dockerfile
FROM postgres:15-alpine

# Set environment variables for PostgreSQL
# These will be used to create the initial database and user
ENV POSTGRES_USER=myuser
ENV POSTGRES_PASSWORD=mypassword
ENV POSTGRES_DB=mydatabase

# Expose PostgreSQL port
EXPOSE 5432

# Optional: Copy initialization scripts
# Any .sql or .sh files in /docker-entrypoint-initdb.d/ run on first startup
# COPY ./init-scripts/ /docker-entrypoint-initdb.d/

# The postgres:15-alpine image automatically starts PostgreSQL
# No CMD needed - the base image handles it
