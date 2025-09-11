import boto3


class StreamableProtoFileS3DatasetExplorer:
    def __init__(self, bucket: str, s3_client=None):
        self.bucket = bucket
        if s3_client is None:
            raise ValueError("s3_client must be provided")
        else:
            self.s3_client = s3_client
        # JSON schema for metadata.json
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

    def get_index_descriptors(self, prefix: str):
        """
        Retrieve index descriptors from metadata.json in the given prefix.
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
        1. Check if a dataset is ready by verifying the presence of 'metadata.json' in the given prefix.
        2. Validate 'metadata.json' against a predefined schema.
        3. Check that number of files in the prefix is equal to 2 + number of index files specified in metadata.json.
        """
        import json
        try:
            # 1. Check for metadata.json and load it
            response = self.s3_client.get_object(Bucket=self.bucket, Key=f"{prefix}/metadata.json")
            metadata_content = response['Body'].read().decode('utf-8')
            metadata = json.loads(metadata_content)

            # 2. Validate metadata.json against schema
            try:
                import jsonschema
                jsonschema.validate(instance=metadata, schema=self._metadata_schema)
            except ImportError:
                print("jsonschema package is required for schema validation.")
                return False
            except jsonschema.ValidationError as ve:
                print(f"Schema validation error: {ve}")
                return False

            # 3. Check file count: 2 + number of index files
            # 2 files: metadata.json and data file (assumed to be present)
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
        paginator = self.s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

        for page in page_iterator:
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if key.endswith("/metadata.json"):
                        # Remove 'metadata.json' from the end and yield
                        yield key[: -len("/metadata.json")]