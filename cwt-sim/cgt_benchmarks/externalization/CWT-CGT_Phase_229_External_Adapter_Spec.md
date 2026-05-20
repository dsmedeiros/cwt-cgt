# Phase 229 — External Adapter Spec

## Canonical external schema

### nodes.parquet / nodes.csv
- node_id
- node_type
- lat / lon (if available)
- region / cluster (optional)
- metadata JSON blob

### edges.parquet / edges.csv
- src
- dst
- weight
- edge_type
- directed
- metadata JSON blob

### states.parquet / states.csv
- timestamp
- node_id
- value_name
- value
- quality flag

### events.parquet / events.csv
- event_id
- start_time
- end_time
- src_node_id (optional)
- dst_node_id (optional)
- event_type
- payload JSON blob

### observations.parquet / observations.csv
- timestamp
- node_id
- observed_flag
- censor_type
- lag_seconds
- release_window_id

### controls.parquet / controls.csv
- timestamp
- control_name
- control_value
- scope (global / node / edge / region)

## Required adapter outputs
Every external adapter must emit:
1. canonical graph bundle
2. observation bundle
3. control bundle
4. benchmark split definition
5. provenance metadata

## Minimal pilot outputs
For first-pass externalization, each adapter may output CSV instead of parquet as long as column names match this schema.
