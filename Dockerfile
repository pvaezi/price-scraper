FROM python:3.10 as build-image

# Include global arg in this stage of the build
ENV DEBIAN_FRONTEND noninteractive
ENV GECKODRIVER_VER v0.31.0
ENV FIREFOX_VER 95.0.1
ENV PLATFORM linux64

# Install geckodriver
RUN GECKODRIVER_SETUP=geckodriver-setup.tar.gz && \
    wget -O $GECKODRIVER_SETUP https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VER}/geckodriver-${GECKODRIVER_VER}-${PLATFORM}.tar.gz && \
    tar -zxf $GECKODRIVER_SETUP -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm $GECKODRIVER_SETUP

# Install firefox
RUN FIREFOX_SETUP=firefox-setup.tar.bz2 && \
    wget -O $FIREFOX_SETUP "https://download.mozilla.org/?product=firefox-${FIREFOX_VER}&os=${PLATFORM}" && \
    tar xjf $FIREFOX_SETUP -C /usr/local/bin && \
    rm $FIREFOX_SETUP

# Copy function code
COPY . /app

# Install the function's dependencies
RUN pip install "/app[postgres,s3]"

# Use a slim version of the base Python image to reduce the final image size
FROM python:3.10-slim

# Install binaries needed by the package
RUN apt-get update && \
    # needed by firefox
    apt-get install -y libxtst6 libgtk-3-0 libx11-xcb-dev libdbus-glib-1-2 libxt6 libpci-dev \
    # needed by postgres
    libpq-dev libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy files needed from first stage in the finalized slim image
COPY --from=build-image /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=build-image /app /app
COPY --from=build-image /usr/local/bin/geckodriver /usr/local/bin/geckodriver
COPY --from=build-image /usr/local/bin/firefox /usr/local/bin/firefox
COPY --from=build-image /usr/local/bin/price_scraper /usr/local/bin/price_scraper

# Add firefox to the path
ENV PATH="/usr/local/bin/firefox/:$PATH"

# Create a non-root user and group
RUN groupadd appgroup --gid 2000  \
    && useradd appuser \
    --create-home \
    --home-dir /app \
    --gid 2000 \
    --shell /bin/bash \
    --uid 1000

# Change the ownership of the /app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# NOTE duckdb to connect to s3 it needs to have httpfs installed
RUN python -c "import duckdb; duckdb.query('INSTALL httpfs;');";

# Pass the name of the function handler as an argument to the runtime
CMD [ "price_scraper" ]
