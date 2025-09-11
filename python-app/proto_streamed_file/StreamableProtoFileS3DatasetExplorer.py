import boto3


class StreamableProtoFileS3DatasetExplorer:
    """
    S3-based dataset explorer for streamable protobuf file datasets.
    
    Provides functionality to explore, validate, and retrieve metadata about 
    protobuf datasets stored in S3 buckets. Each dataset is expected to have
    a metadata.json file describing indexes, tags, and data properties (such as record count),
    along with associated data and index files.
    """
    def __init__(self, bucket: str, s3_client=None):
        """
        Initialize the dataset explorer.
        
        Args:
            bucket (str): S3 bucket name containing the datasets
            s3_client: Boto3 S3 client instance (required)
            
        Raises:
            ValueError: If s3_client is not provided
        """
        self.bucket = bucket
        if s3_client is None:
            raise ValueError("s3_client must be provided")
        else:
            self.s3_client = s3_client
        # JSON schema for metadata.json (updated to include 'data' property)
        self._metadata_schema = {
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
                "data": {
                    "type": "object",
                    "properties": {
                        "records": { "type": "integer" }
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
            "required": ["indexes"]
        }

    def get_dataset_descriptor(self, prefix: str):
        """
        Retrieve complete dataset information including metadata and file listings.
        The metadata will include 'indexes', 'tags', and 'data' (e.g., record count).
        
        Args:
            prefix (str): S3 prefix/path containing the dataset
        Returns:
            dict: Dictionary containing 'metadata' (from metadata.json, including 'data'),
                  and 'files' (list of file details with name, size, and last_modified)
        """
        import json
        try:
            # 1. Retrieve metadata.json
            response = self.s3_client.get_object(Bucket=self.bucket, Key=f"{prefix}/metadata.json")
            metadata_content = response['Body'].read().decode('utf-8')
            metadata = json.loads(metadata_content)

            # 2. List all files in the prefix (excluding subfolders)
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
            files = []
            for page in page_iterator:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        # Only include files directly under the prefix (not in subfolders)
                        if key.startswith(prefix) and key[len(prefix):].count("/") <= 1:
                            files.append({
                                "name": key[len(prefix):].lstrip("/"),
                                "size": obj.get("Size"),
                                "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None
                            })

            # 3. Return combined dictionary
            return {
                "metadata": metadata,
                "files": files
            }
        except Exception as e:
            print(f"Error retrieving dataset descriptor: {e}")
            return {}
        
    def get_index_descriptors(self, prefix: str):
        """
        Retrieve index information from dataset metadata.
        
        Args:
            prefix (str): S3 prefix/path containing the dataset
            
        Returns:
            list: List of index descriptors from metadata.json
        """
        import json
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=f"{prefix}/metadata.json")
            metadata_content = response['Body'].read().decode('utf-8')
            metadata = json.loads(metadata_content)
            return metadata.get("indexes", [])
        except Exception as e:
            print(f"Error retrieving index descriptors: {e}")
            return []

    def is_dataset_ready(self, prefix: str) -> bool:
        """
        Validate dataset completeness and schema compliance.
        
        Checks for metadata.json presence, validates against updated schema (including 'data'),
        and verifies expected file count (2 base files + index files).
        
        Args:
            prefix (str): S3 prefix/path containing the dataset
        Returns:
            bool: True if dataset is complete and valid
        """
        import json
        try:
            # 1. Check for metadata.json and load it
            response = self.s3_client.get_object(Bucket=self.bucket, Key=f"{prefix}/metadata.json")
            metadata_content = response['Body'].read().decode('utf-8')
            metadata = json.loads(metadata_content)

            # 2. Validate metadata.json against updated schema
            try:
                import jsonschema
                jsonschema.validate(instance=metadata, schema=self._metadata_schema)
            except ImportError:
                print("jsonschema package is required for schema validation.")
                return False
            except jsonschema.ValidationError as ve:
                print(f"Schema validation error: {ve}")
                return False

            # 3. Check file count: 2 + number of index files (metadata.json, data file, index files)
            expected_file_count = 2 + len(metadata.get("indexes", []))
         

            # List all files in the prefix
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
            file_count = 0
            for page in page_iterator:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        # Only count files directly under the prefix (not in subfolders)
                        key = obj["Key"]
                        if key.startswith(prefix) and key[len(prefix):].count("/") <= 1:
                            file_count += 1

            if file_count != expected_file_count:
                print(f"File count mismatch: found {file_count}, expected {expected_file_count}")
                return False

            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            print(f"Error checking dataset readiness: {e}")
            return False

    def list_datasets(self, prefix: str = ""):
        """
        Discover available datasets in the S3 bucket.
        
        Args:
            prefix (str): Optional prefix to filter dataset search
            
        Yields:
            str: Dataset prefix paths (directories containing metadata.json)
        """
        paginator = self.s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

        for page in page_iterator:
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if key.endswith("/metadata.json"):
                        # Remove 'metadata.json' from the end and yield
                        yield key[: -len("/metadata.json")]