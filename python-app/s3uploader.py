import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def upload_file_to_minio(file_path, bucket_name, object_name=None, endpoint_url=None, access_key=None, secret_key=None, region_name="us-east-1"):
	"""
	Upload a file to an S3-compatible MinIO bucket.

	:param file_path: Path to the file to upload
	:param bucket_name: Name of the bucket to upload to
	:param object_name: S3 object name. If not specified, file_path's basename is used
	:param endpoint_url: MinIO server endpoint URL (e.g., 'http://localhost:9000')
	:param access_key: MinIO access key
	:param secret_key: MinIO secret key
	:param region_name: AWS region (default: 'us-east-1')
	:return: True if file was uploaded, else False
	"""
	import os
	if object_name is None:
		object_name = os.path.basename(file_path)

	s3_client = boto3.client(
		's3',
		endpoint_url=endpoint_url,
		aws_access_key_id=access_key,
		aws_secret_access_key=secret_key,
		region_name=region_name,
	)
	try:
		s3_client.upload_file(file_path, bucket_name, object_name)
		print(f"Upload Successful: {file_path} -> s3://{bucket_name}/{object_name}")
		return True
	except FileNotFoundError:
		print("The file was not found.")
		return False
	except NoCredentialsError:
		print("Credentials not available.")
		return False
	except ClientError as e:
		print(f"Client error: {e}")
		return False

if __name__ == "__main__":
    upload_file_to_minio(
		file_path="../app/name.index",
		bucket_name="large-proto-files",
		object_name="/xfer/2020-01-09/RISK_SCENARIOS,1,0,EOD,2025-09-10, 7e7da23a-c235-4769-b268-d5a1b9b4542f~proto_risk~5.0.0.binpb/symbol.index",
		endpoint_url="http://localhost:9000",
		access_key="minioadmin",
		secret_key="minioadmin",
		region_name="us-east-1",
	)
	
    '''import argparse
	parser = argparse.ArgumentParser(description="Upload a file to MinIO (S3 compatible)")
	parser.add_argument("file_path", help="Path to the file to upload")
	parser.add_argument("bucket_name", help="Bucket name")
	parser.add_argument("--object_name", help="Object name in bucket (default: basename of file)")
	parser.add_argument("--endpoint_url", required=True, help="MinIO endpoint URL, e.g. http://localhost:9000")
	parser.add_argument("--access_key", required=True, help="MinIO access key")
	parser.add_argument("--secret_key", required=True, help="MinIO secret key")
	parser.add_argument("--region_name", default="us-east-1", help="AWS region (default: us-east-1)")
	args = parser.parse_args()

	upload_file_to_minio(
		file_path=args.file_path,
		bucket_name=args.bucket_name,
		object_name=args.object_name,
		endpoint_url=args.endpoint_url,
		access_key=args.access_key,
		secret_key=args.secret_key,
		region_name=args.region_name,
	)    '''	
		
