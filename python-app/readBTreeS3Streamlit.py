from proto_streamed_file.S3BPlusTreeSeeker import S3BPlusTreeSeeker
from proto.PricesStreamedFileHeader_pb2 import PricesStreamedFileHeader
from proto.PricesStreamedFilePayload_pb2 import PricesStreamedFilePayload
from proto_streamed_file.StreamableProtoFileS3Parser import StreamableProtoFileS3Parser

from proto_streamed_file.StreamableProtoFileS3BucketExplorer import StreamableProtoFileS3BucketExplorer

import boto3
from botocore.client import Config
from botocore import UNSIGNED
import streamlit as st
import time
import pandas as pd

boto3.setup_default_session()

s3_client = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    region_name="us-east-1",
)

bucket = "large-proto-files"
prefix = "xfer/2020-01-10/RISK_SCENARIOS,1,0,EOD,2025-09-10, 7e7da23a-c235-4769-b268-d5a1b9b4542f~proto_risk~5.0.0.binpb/"




tree = S3BPlusTreeSeeker(
    bucket=bucket,
    key=f"{prefix}symbol.index",
    s3_client=s3_client
)


with StreamableProtoFileS3Parser(bucket, f"{prefix}data.binpb", PricesStreamedFileHeader, PricesStreamedFilePayload, s3_client) as parser:
    header = parser.getHeader()

    print(f"Header: {header}")
    badge_placeholder = st.empty()
    symbol = st.text_input("Symbol Search")

    start_time = time.time()
    prices = []
    for value in tree.search(symbol.encode("utf-8")):
        offset = int.from_bytes(value, byteorder="big")
        payload = parser.getPayloadAtOffset(offset)
        end_time = time.time()
        badge_placeholder.badge(f"{end_time - start_time:.6f} seconds", color="green")
        for p in payload.price.prices:
            prices.append(p)

    if prices:
        st.write(f'Prices for {payload.price.name}:')
        df = pd.DataFrame(prices)
        st.dataframe(df)

    explorer = StreamableProtoFileS3BucketExplorer(bucket=bucket, s3_client=s3_client)
    for filename in explorer.list_files(prefix="xfer"):
        st.write(filename)


    option = st.selectbox(
    "Choose file",
    ("Email", "Home phone", "Mobile phone"),
    )