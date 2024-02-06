# Price Scraper

[See Changelog](./CHANGELOG.md)

## Overview

This lightweight package provides web scraping capability specific to getting product prices from retailers.
It leverages Selenium for scraping content of websites, with extensibility to different retailers business logic as well as extendable storage options.

## Local Install

You need to install [Firefox](https://www.mozilla.org/en-US/firefox/all/#product-desktop-release) and [Geckodriver](https://firefox-source-docs.mozilla.org/testing/geckodriver/index.html) on the operating system first.

Then you can pip install the package via

```bash
pip install price-scraper[postgres,s3]
```

Above command would install the base package as well as `postgres` extras dependencies to work with postgres storage to store scraped data.

You can look into `setup.cfg` to see what extras is needed based on the storage you are intending to use.

For local development, if you need to add new scraping/storage capabilities, you can install the git cloned directory with all necessary extras:

```bash
git clone git@github.com:pvaezi/price-scraper.git
cd price-scraper
pip install -e .[postgres,s3,dev]
```

## Executing a Scraping Command

We can issue a scraping command via provided CLI.
We just need to pass in the JSON payload (or actual JSON file) that contains basic information about scraping, destination storage, and optionally proxy.

```bash
price_scraper \
  --retailer AMZ \
  --url https://www.amazon.com/stores/page/D209D922-7883-495C-9894-6B13D9BB1A67 \
  --brand Apple \
  --category "Electronics/Computers&Accessories/Computers&Tablets/Laptops" \
  --storage-config '{"storage_type": "S3", "storage_options": {"bucket_and_prefix": "s3://<BUCKET>/<PREFIX>", "region": "<REGION>"}}' \
  --proxy-config '{"httpProxy": "<PROXY>:<PORT>", "sslProxy": "<PROXY>:<PORT>", "proxyType": "MANUAL"}' \
  --timeout 30
```

Scraping schema includes:

- `retailer`: The name of retailer enum that is supported. Supported retailers should have a repository subclass of `price_scraper/retailer/` folder as well as exist in the supported [Enums](./price_scraper/enums.py).
- `url`: The URL of retailer to scrape.
- `category`: Freeform string of the category of products being scraped. If the string is separated by `/`, it would store them as a string of strings in the storage to account for sub-categories.
- `brand`: The products brand. Scraped page must belong to a single product page at the moment.
- `storage-config`: The type of storage to save the scraped data to. Accepts plurals. Can store into one or more storage repositories in a single scraping command in this format `--storage-config <storage_1_config> <storage_2_config>`.
  - Must include enum value for `storage_type` key, which indicates the repository class that needs to be used. The enum must exist in the supported [Enums](./price_scraper/enums.py).
  - `storage_options` is a freeform keyword argument dictionary that provides necessary arguments to the repository class instantiation.
- `proxy-config`: The proxy configuration for Selenium. It is optional, but recommended to configure for large scale scraping.
- `timeout`: Page loading timeout. It is optional, and defaults to 30 seconds.

You can read Pydantic schemas [here](./price_scraper/cli.py) to learn more about the schema.

## Containerized Deployment

You can also use provided `Dockerfile` to make container out of the package and deploy it on to your local or production Kubernetes cluster.

The Firefox container build currently only supports `amd64` architecture.

```bash
docker build --platform linux/amd64 --progress=plain -t <IMAGE>:<TAG> .
```

Once you add the newly built image to your container registry you can create a sample job similar to below specs to perform scraping.

Here is an sample of a Kubernetes batch job that performs scraping of a single grid product page.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sample-scraper
spec:
  ttlSecondsAfterFinished: 10
  template:
    spec:
      containers:
        - name: sample-scraper
          image: <IMAGE>:<TAG>
          command: ["price_scraper"]
          imagePullPolicy: IfNotPresent
          args:
            [
              "--retailer",
              "AMZ",
              "--url",
              "https://www.amazon.com/stores/page/D209D922-7883-495C-9894-6B13D9BB1A67",
              "--brand",
              "Apple",
              "--category",
              "Electronics/Computers&Accessories/Computers&Tablets/Laptops",
              "--storage-config",
              '{"storage_type": "S3", "storage_options": {"bucket_and_prefix": "s3://<BUCKET>/<PREFIX>", "region": "<REGION>"}}',
              '{"storage_type": "POSTGRES"}',
              "--timeout",
              "30",
            ]
          env:
            - name: POSTGRES_USER
              value: postgres
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-postgresql
                  key: postgres-password
          volumeMounts:
            - name: aws-creds
              mountPath: "/app/.aws"
              readOnly: true
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 2000
      volumes:
        - name: aws-creds
          secret:
            secretName: aws-credentials
            items:
              - key: credentials
                path: credentials
      restartPolicy: Never
  backoffLimit: 4
```

You can simply apply the spec:

```bash
kubectl apply -f spec.yml
```
