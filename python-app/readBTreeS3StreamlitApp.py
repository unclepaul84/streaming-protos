
# Import custom modules for S3 B+Tree search and proto parsing
from proto_streamed_file.S3BPlusTreeSeeker import S3BPlusTreeSeeker
from proto.PricesStreamedFileHeader_pb2 import PricesStreamedFileHeader
from proto.PricesStreamedFilePayload_pb2 import PricesStreamedFilePayload
from proto_streamed_file.StreamableProtoFileS3Parser import StreamableProtoFileS3Parser
from proto_streamed_file.StreamableProtoFileS3DatasetExplorer import StreamableProtoFileS3DatasetExplorer


# Import required libraries
import boto3
from botocore.client import Config
from botocore import UNSIGNED
import streamlit as st
import time
import pandas as pd


# Set up default boto3 session
boto3.setup_default_session()


# Configure S3 client for MinIO (local S3-compatible storage)
s3_client = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    region_name="us-east-1",
)

# S3 bucket name
bucket = "large-proto-files"

# Create dataset explorer for the S3 bucket
explorer = StreamableProtoFileS3DatasetExplorer(bucket=bucket, s3_client=s3_client)

# List available datasets with prefix 'xfer'
datasets = []
for filename in explorer.list_datasets(prefix="xfer"):
    datasets.append(filename)

# Streamlit dropdown to select dataset
dataset_choice = st.selectbox(
    "Choose Dataset",
    datasets,
)

# check if dataset is available
if not explorer.is_dataset_ready(dataset_choice):
    st.error(f"Dataset '{dataset_choice}' is not ready. Please ensure 'metadata.json' is present and valid.")
    st.stop()

# Get index descriptors for the selected dataset
index_descriptors = explorer.get_index_descriptors(dataset_choice)

with st.expander("Descriptor"):
    st.json(explorer.get_dataset_descriptor(dataset_choice))
# Streamlit dropdown to select index file
index_choice = st.selectbox(
    "Choose index",
    [idx["file"] for idx in index_descriptors],
)

# Prefix for S3 keys
prefix = dataset_choice + "/"

# Initialize B+Tree seeker for the selected index
tree = S3BPlusTreeSeeker(
    bucket=bucket,
    key=f"{prefix}{index_choice}",
    s3_client=s3_client
)

# Find the selected index descriptor
selected_index = next((idx for idx in index_descriptors if idx["file"] == index_choice), None)

# Open the proto file parser for the selected dataset
with StreamableProtoFileS3Parser(bucket, f"{prefix}data.binpb", PricesStreamedFileHeader, PricesStreamedFilePayload, s3_client) as parser:
    header = parser.getHeader()  # Read file header
   
    search_term = st.text_input(f"{selected_index['description']}. Field: {selected_index['field']}", value="AAPL100")  # User search input

    start_time = time.time()
    prices = []
    # Search for the term in the B+Tree index
    for value in tree.search(search_term.encode("utf-8")):
        offset = int.from_bytes(value, byteorder="big")  # Convert bytes to offset
        payload = parser.getPayloadAtOffset(offset)  # Get payload at offset
        end_time = time.time()
        
        for p in payload.price.prices:
            prices.append(p)  # Collect prices

    # Display results in a table if found
    if prices:
        st.badge(f"Search time: {end_time - start_time:.6f} seconds", color="green")  # Show search time
        st.write(f'Prices for {payload.price.name}:')
        df = pd.DataFrame(prices)
        st.dataframe(df)

