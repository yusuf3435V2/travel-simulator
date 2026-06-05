"""Unit tests for s3_utils_sim module using moto for AWS mocking."""

import pytest
import boto3
import networkx as nx
import pandas as pd
import json
from unittest.mock import patch
from moto import mock_aws
from s3_utils_sim import (
    load_env_variables,
    check_baseline_exists_in_s3,
    fetch_graph_from_s3,
    save_dataframe_to_s3,
    load_csv_results_from_s3,
    save_json_to_s3,
)


# Tests for load_env_variables function


def test_load_env_variables_success(monkeypatch) -> None:
    """Test that load_env_variables returns the S3_BUCKET_NAME when set."""
    monkeypatch.setenv("S3_BUCKET_NAME", "TEST_S3_BUCKET")
    bucket_name = load_env_variables()
    assert bucket_name == "TEST_S3_BUCKET"


def test_load_env_variables_missing_raises_error(monkeypatch) -> None:
    """Test that load_env_variables raises ValueError when S3_BUCKET_NAME is not set."""
    # Clear any existing S3_BUCKET_NAME
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    # Mock dotenv.load_dotenv to prevent loading from .env file
    with patch("s3_utils_sim.dotenv.load_dotenv"):
        with pytest.raises(ValueError) as exc_info:
            load_env_variables()
        assert "S3_BUCKET_NAME" in str(exc_info.value)


def test_load_env_variables_custom_bucket_name(monkeypatch) -> None:
    """Test that load_env_variables returns custom bucket names correctly."""
    monkeypatch.setenv("S3_BUCKET_NAME", "MY_CUSTOM_BUCKET")
    bucket_name = load_env_variables()
    assert bucket_name == "MY_CUSTOM_BUCKET"


# Tests for check_baseline_exists_in_s3 function


@mock_aws
def test_baseline_exists(aws_credentials, monkeypatch) -> None:
    """Test that check_baseline_exists_in_s3 returns True when BASELINE.csv exists."""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")
    s3_client.put_object(Bucket="test-bucket", Key="raw/BASELINE.csv", Body=b"data")

    result = check_baseline_exists_in_s3()
    assert result is True


@mock_aws
def test_baseline_does_not_exist(aws_credentials, monkeypatch) -> None:
    """Test that check_baseline_exists_in_s3 returns False when BASELINE.csv does not exist."""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")
    s3_client.put_object(Bucket="test-bucket", Key="raw/other_file.csv", Body=b"data")

    result = check_baseline_exists_in_s3()
    assert result is False


@mock_aws
def test_baseline_empty_bucket(aws_credentials, monkeypatch) -> None:
    """Test that check_baseline_exists_in_s3 returns False when bucket is empty."""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")

    result = check_baseline_exists_in_s3()
    assert result is False


@mock_aws
def test_baseline_exception_handling(aws_credentials, monkeypatch) -> None:
    """Test that check_baseline_exists_in_s3 returns False when S3 bucket does not exist."""
    monkeypatch.setenv("S3_BUCKET_NAME", "nonexistent-bucket")

    result = check_baseline_exists_in_s3()
    assert result is False


# Tests for fetch_graph_from_s3 function


@mock_aws
def test_fetch_graph_from_s3_success(aws_credentials, mock_graph_xml: str) -> None:
    """Test that fetch_graph_from_s3 successfully fetches and parses a 2-station graph."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")
    s3_client.put_object(
        Bucket="test-bucket",
        Key="processed/stations_network.graphml",
        Body=mock_graph_xml.encode("utf-8"),
    )

    result = fetch_graph_from_s3("test-bucket")

    assert isinstance(result, nx.Graph)
    assert result.number_of_nodes() == 2
    assert result.number_of_edges() == 1
    assert "station1" in result.nodes()
    assert "station2" in result.nodes()


@mock_aws
def test_fetch_graph_from_s3_parse_error(aws_credentials) -> None:
    """Test that fetch_graph_from_s3 returns empty graph on parse error."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")
    s3_client.put_object(
        Bucket="test-bucket",
        Key="processed/stations_network.graphml",
        Body=b"invalid xml content",
    )

    result = fetch_graph_from_s3("test-bucket")

    assert isinstance(result, nx.Graph)
    assert result.number_of_nodes() == 0
    assert result.number_of_edges() == 0


@mock_aws
def test_fetch_graph_from_s3_s3_error(aws_credentials) -> None:
    """Test that fetch_graph_from_s3 returns empty graph when S3 access fails."""
    result = fetch_graph_from_s3("nonexistent-bucket")

    assert isinstance(result, nx.Graph)
    assert result.number_of_nodes() == 0
    assert result.number_of_edges() == 0


@mock_aws
def test_fetch_graph_from_s3_empty_file(aws_credentials) -> None:
    """Test that fetch_graph_from_s3 returns empty graph when the file is empty."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")
    s3_client.put_object(
        Bucket="test-bucket",
        Key="processed/stations_network.graphml",
        Body=b"",
    )

    result = fetch_graph_from_s3("test-bucket")

    assert isinstance(result, nx.Graph)
    assert result.number_of_nodes() == 0
    assert result.number_of_edges() == 0


# Tests for save_dataframe_to_s3 function


@mock_aws
def test_save_dataframe_to_s3_success(aws_credentials) -> None:
    """Test that save_dataframe_to_s3 successfully saves a normal DataFrame to S3."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")

    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    save_dataframe_to_s3(df, "test-bucket", "data/results.csv")

    # Verify the file was saved to S3
    obj = s3_client.get_object(Bucket="test-bucket", Key="data/results.csv")
    saved_content = obj["Body"].read().decode("utf-8")
    assert "col1" in saved_content
    assert "col2" in saved_content
    assert "1" in saved_content
    assert "a" in saved_content


@mock_aws
def test_save_dataframe_to_s3_empty_dataframe(aws_credentials) -> None:
    """Test that save_dataframe_to_s3 successfully saves an empty DataFrame to S3."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")

    df = pd.DataFrame()
    save_dataframe_to_s3(df, "test-bucket", "data/empty_results.csv")

    # Verify the file was saved to S3
    obj = s3_client.get_object(Bucket="test-bucket", Key="data/empty_results.csv")
    saved_content = obj["Body"].read().decode("utf-8")
    assert saved_content == "\n"


@mock_aws
def test_save_dataframe_to_s3_handles_incorrect_datatype(aws_credentials) -> None:
    """Test that save_dataframe_to_s3 handles incorrect datatype gracefully."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")

    df = {"col1": [1, 2], "col2": ["x", "y"]}
    with pytest.raises(ValueError):
        save_dataframe_to_s3(df, "test-bucket", "data/error_results.csv")


# Tests for load_csv_results_from_s3 function


@mock_aws
def test_load_results_from_s3_success(aws_credentials, csv_content: str) -> None:
    """Test that load_csv_results_from_s3 successfully loads a CSV file from S3."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")
    s3_client.put_object(
        Bucket="test-bucket",
        Key="data/results.csv",
        Body=csv_content.encode("utf-8"),
    )

    result = load_csv_results_from_s3("test-bucket", "data/results.csv")

    assert isinstance(result, pd.DataFrame)
    assert result.shape == (3, 2)
    assert list(result.columns) == ["col1", "col2"]
    assert result["col1"].tolist() == [1, 2, 3]
    assert result["col2"].tolist() == ["a", "b", "c"]


@mock_aws
def test_load_results_from_s3_empty_file(aws_credentials) -> None:
    """Test that load_csv_results_from_s3 handles empty CSV files correctly."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")
    csv_content = "col1,col2\n"
    s3_client.put_object(
        Bucket="test-bucket",
        Key="data/empty.csv",
        Body=csv_content.encode("utf-8"),
    )

    result = load_csv_results_from_s3("test-bucket", "data/empty.csv")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
    assert "col1" in result.columns
    assert "col2" in result.columns


@mock_aws
def test_load_results_from_s3_s3_error(aws_credentials) -> None:
    """Test that load_csv_results_from_s3 returns empty DataFrame on S3 errors."""
    result = load_csv_results_from_s3("nonexistent-bucket", "data/results.csv")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


# Tests for save_json_to_s3 function


@mock_aws
def test_save_json_to_s3_success(aws_credentials) -> None:
    """Test that save_json_to_s3 successfully saves JSON data to S3."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")

    json_data = {
        "simulation_id": "sim_001",
        "metrics": {"avg_time": 45.5, "total_passengers": 1000},
    }
    save_json_to_s3(json_data, "test-bucket", "data/results.json")

    # Verify the file was saved to S3
    obj = s3_client.get_object(Bucket="test-bucket", Key="data/results.json")
    saved_content = obj["Body"].read().decode("utf-8")
    saved_json = json.loads(saved_content)
    assert saved_json["simulation_id"] == "sim_001"
    assert saved_json["metrics"]["avg_time"] == 45.5


@mock_aws
def test_save_json_to_s3_empty_dict(aws_credentials) -> None:
    """Test that save_json_to_s3 handles empty dictionaries correctly."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")

    json_data = {}
    save_json_to_s3(json_data, "test-bucket", "data/empty.json")

    # Verify the file was saved to S3
    obj = s3_client.get_object(Bucket="test-bucket", Key="data/empty.json")
    saved_content = obj["Body"].read().decode("utf-8")
    assert saved_content == "{}"


@mock_aws
def test_save_json_to_s3_nested_dict(aws_credentials) -> None:
    """Test that save_json_to_s3 handles deeply nested dictionaries correctly."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="test-bucket")

    json_data = {"key": "value", "nested": {"inner": "data", "deep": {"level": 3}}}
    save_json_to_s3(json_data, "test-bucket", "data/results.json")

    # Verify the file was saved to S3
    obj = s3_client.get_object(Bucket="test-bucket", Key="data/results.json")
    saved_content = obj["Body"].read().decode("utf-8")
    saved_json = json.loads(saved_content)
    assert saved_json["nested"]["deep"]["level"] == 3
