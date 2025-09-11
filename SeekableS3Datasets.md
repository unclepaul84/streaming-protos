# Seekable S3 Datasets - Specification and Usage Guide

## Overview

This document describes the specification for streaming protobuf datasets stored in Amazon S3, designed for efficient random access and streaming operations. The format enables reading large datasets without downloading entire files, using B+Tree indexes for fast lookups and S3 range requests for minimal bandwidth usage.

## S3 Directory Structure

### Dataset Organization

Each dataset is organized as a directory (S3 prefix) containing the following standardized file structure:

```
bucket/
└── dataset-prefix/
    ├── metadata.json          # Dataset metadata and index definitions
    ├── data.binpb            # Main streamable protobuf data file
    ├── {index-name}.index    # B+Tree index files (one per index)
```

### Directory Structure Examples


#### Hierarchical Organization
```
s3://my-bucket/
├── xfer/
│   └── 2024-01-10/
│       └── RISK_SCENARIOS,1,0,EOD,2024-01-10,uuid~proto_risk~5.0.0.binpb/
│           ├── metadata.json
│           ├── data.binpb
│           └── symbol.index

```

## File Specifications

### 1. Main Data File (`data.binpb`)

The primary data file follows the streaming protobuf format specification:

**Binary Layout:**
```
[Magic Byte: 4 bytes] [Header Length: 4 bytes] [Header: variable] 
[Payload Length: 4 bytes] [Payload: variable] ...
[File Seal: 4 bytes (-1)]
```

**Properties:**
- Magic Byte: `0x1973` (constant)
- All integers: 4-byte, signed, big-endian
- Header and Payloads: Protocol Buffer serialized byte arrays
- File Seal: `-1` marker indicating end of file

### 2. Index Files (`*.index`)

B+Tree index files providing efficient key-to-offset mapping:

**Structure:**
- Binary B+Tree format optimized for range reads
- Keys: Byte arrays (typically UTF-8 encoded strings)
- Values: 8-byte big-endian integers (file offsets)
- Support for prefix searches and range queries

### 3. Metadata File (`metadata.json`)

JSON file containing dataset configuration and index definitions.

## Metadata Schema

### Required Structure

```json
{
  "indexes": [
    {
      "file": "symbol.index",
      "description": "Symbol-based search. Example: AAPL100",
      "field": "price.name"
    },
    {
      "file": "date.index", 
      "description": "Date-based search. Example: 2024-01-15",
      "field": "price.date"
    }
  ],
  "tags": [
    {
      "name": "pillar",
      "value": "risk"
    },
    {
      "name": "version",
      "value": "5.0.0"
    }
  ]
}
```

### Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "indexes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file": { "type": "string" },
          "description": { "type": "string" },
          "field": { "type": "string" }
        },
        "required": ["file", "description", "field"]
      }
    },
    "tags": {
      "type": "array", 
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "value": { "type": "string" }
        },
        "required": ["name", "value"]
      }
    }
  },
  "required": ["indexes", "tags"]
}
```

### Field Descriptions

**Indexes Array:**
- `file`: Name of the index file (e.g., "symbol.index")
- `description`: Human-readable description with usage examples
- `field`: Dot-notation path to the indexed protobuf field (e.g., "price.name")

**Tags Array:**
- `name`: Tag name for categorization/filtering
- `value`: Tag value for identification

## Dataset Readiness Calculation

### Readiness Criteria

A dataset is considered "ready" when all of the following conditions are met:

1. **Metadata Presence**: `metadata.json` file exists and is accessible
2. **Schema Validation**: `metadata.json` conforms to the required JSON schema
3. **File Count Verification**: Expected number of files are present
4. **File Accessibility**: All referenced files can be accessed

### Calculation Algorithm

```python
def is_dataset_ready(prefix: str) -> bool:
    try:
        # 1. Check metadata.json presence and load
        metadata = load_metadata_json(prefix)
        
        # 2. Validate against schema
        if not validate_schema(metadata):
            return False
            
        # 3. Calculate expected file count
        # Base files: metadata.json + data.binpb = 2
        # Index files: one per index definition
        expected_count = 2 + len(metadata.get("indexes", []))
        
        # 4. Count actual files in prefix
        actual_count = count_files_in_prefix(prefix)
        
        # 5. Verify counts match
        return actual_count == expected_count
        
    except (FileNotFoundError, ValidationError, Exception):
        return False
```

### Readiness States

| State | Description | Actions Available |
|-------|-------------|------------------|
| **Ready** | All files present, metadata valid | Full read/search operations |
| **Incomplete** | Missing files or invalid metadata | Limited operations, error reporting |
| **Not Found** | Dataset prefix doesn't exist | Dataset creation required |

## Usage Patterns

### 1. Dataset Discovery

```python
# Python example
explorer = StreamableProtoFileS3DatasetExplorer(bucket="my-bucket", s3_client=s3_client)

# List all datasets
for dataset_prefix in explorer.list_datasets():
    if explorer.is_dataset_ready(dataset_prefix):
        print(f"Ready: {dataset_prefix}")
    else:
        print(f"Not ready: {dataset_prefix}")
```


### 2. Metadata Inspection

```python
# Get complete dataset information
descriptor = explorer.get_dataset_descriptor("prices-2024-01-15")
print(f"Metadata: {descriptor['metadata']}")
print(f"Files: {descriptor['files']}")

# Get index information only
indexes = explorer.get_index_descriptors("prices-2024-01-15")
for index in indexes:
    print(f"Index: {index['file']} - {index['description']}")
```

### 3. Data Access


#### Indexed Access (Fast Lookups)
```python
# Initialize B+Tree seeker
tree = S3BPlusTreeSeeker(
    bucket=bucket,
    key="prices-2024-01-15/symbol.index", 
    s3_client=s3_client
)

# Search for specific records
search_key = "AAPL100".encode("utf-8")
with StreamableProtoFileS3Parser(bucket, "prices-2024-01-15/data.binpb",
                                  HeaderClass, PayloadClass, s3_client) as parser:
    for offset_bytes in tree.search(search_key):
        offset = int.from_bytes(offset_bytes, byteorder="big")
        payload = parser.getPayloadAtOffset(offset)
        process_payload(payload)
```




## Performance Characteristics

### S3 Range Requests
- **Efficiency**: Only required bytes are fetched from S3
- **Bandwidth**: Minimal data transfer for targeted queries
- **Latency**: Single request per data access operation

### Index Performance
- **Lookup Time**: O(log n) for key searches
- **Memory Usage**: Minimal - index nodes loaded on demand
- **Scalability**: Supports datasets with millions of records

### Streaming Performance
- **Memory Footprint**: Constant memory usage regardless of dataset size
- **Throughput**: Limited by S3 bandwidth and protobuf parsing speed


## Best Practices

### Dataset Design
1. **Index Selection**: Create indexes on frequently queried fields
2. **Key Design**: Use consistent, sortable key formats



## Implementation Languages

### Supported Languages
- **Python**: Complete implementation with boto3

### Library Components
- **Parsers**: StreamableProtoFileS3Parser (Python)
- **Index Seekers**: S3BPlusTreeSeeker (Python)  
- **Explorers**: StreamableProtoFileS3DatasetExplorer (Python)
- **Writers**: StreamableProtoFileWriter (Python)

## Example Applications
[See Here](python-app/readBTreeS3StreamlitApp.py)


This specification provides a complete framework for organizing, validating, and accessing streaming protobuf datasets in S3 with efficient random access capabilities.