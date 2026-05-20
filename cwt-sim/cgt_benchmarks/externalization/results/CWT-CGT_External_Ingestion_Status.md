# External ingestion status

## Successfully ingested
- OEDI IEEE123 repository-backed files from the official OEDI dataset/repository linkage:
  - sensors.json
  - qsts/master.dss
  - qsts/Buscoords.dss
  - multiple real load profiles
  - one real PV profile
  - temperature series

## Schema / endpoint validated but bulk ingest not completed in this environment
- Citi Bike official system-data page and GBFS manifest
- Chicago Traffic Tracker official data.gov / City of Chicago catalog pages and direct CSV download URLs

## Why some sources were only partially ingested
- The current environment can browse official pages and small text/raw files reliably.
- Direct GBFS JSON download and Socrata CSV export were not successfully retrievable through the available file-transfer path here.
- To avoid pretending otherwise, the actual quantitative external pilot in this pass is OEDI-only, while Citi Bike and Chicago remain ready-to-ingest sources with validated endpoints and schemas.
