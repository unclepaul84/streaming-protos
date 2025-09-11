import boto3


class StreamableProtoFileS3BucketExplorer:
    def __init__(self, bucket: str, s3_client=None):
        self.bucket = bucket
        if s3_client is None:
           raise ValueError("s3_client must be provided")
        else:
            self.s3_client = s3_client

    def list_files(self, prefix: str = ""):
        paginator = self.s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

        files = []
        for page in page_iterator:
            if "Contents" in page:
                for obj in page["Contents"]:
                    files.append(obj["Key"])
        return files