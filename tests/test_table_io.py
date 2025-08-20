"""Tests for Table I/O functionality (CSV and Parquet)."""

import csv
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from chidian import Table


class TestTableCSV:
    """Test CSV import/export functionality."""

    def test_csv_round_trip_basic(self):
        """Test basic CSV write and read."""
        data = [
            {"name": "Alice", "age": 30, "city": "NYC"},
            {"name": "Bob", "age": 25, "city": "LA"},
            {"name": "Charlie", "age": 35, "city": "Chicago"},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write to CSV
            table.to_csv(temp_path)

            # Read back
            table2 = Table.from_csv(temp_path)

            # Verify data
            assert len(table2) == len(table)
            assert table2.columns == table.columns

            # Check values
            for i, (row1, row2) in enumerate(zip(table, table2)):
                assert row1 == row2
        finally:
            temp_path.unlink()

    def test_csv_with_custom_delimiter(self):
        """Test CSV with tab delimiter."""
        data = [{"col1": "value1", "col2": "value2"}]
        table = Table(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write with tab delimiter
            table.to_csv(temp_path, delimiter="\t")

            # Read back with tab delimiter
            table2 = Table.from_csv(temp_path, delimiter="\t")

            assert len(table2) == 1
            assert table2.get("$0") == data[0]
        finally:
            temp_path.unlink()

    def test_csv_with_null_values(self):
        """Test handling of null values in CSV."""
        data = [
            {"name": "Alice", "age": 30, "score": None},
            {"name": "Bob", "age": None, "score": 95.5},
            {"name": None, "age": 25, "score": 88.0},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write with custom null value
            table.to_csv(temp_path, null_value="NULL")

            # Read back with null value handling
            table2 = Table.from_csv(temp_path, null_values=["NULL"])

            # Verify nulls are preserved
            assert table2.get("$0.score") is None
            assert table2.get("$1.age") is None
            assert table2.get("$2.name") is None
        finally:
            temp_path.unlink()

    def test_csv_with_type_specification(self):
        """Test CSV reading with explicit type specifications."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)
            f.write("id,value,active\n")
            f.write("1,123.45,true\n")
            f.write("2,67.89,false\n")

        try:
            # Read with explicit types
            table = Table.from_csv(
                temp_path, dtypes={"id": int, "value": float, "active": bool}
            )

            # Verify types
            row0 = table.get("$0")
            assert isinstance(row0["id"], int)
            assert row0["id"] == 1
            assert isinstance(row0["value"], float)
            assert row0["value"] == 123.45
            assert isinstance(row0["active"], bool)
            assert row0["active"] is True
        finally:
            temp_path.unlink()

    def test_csv_with_date_parsing(self):
        """Test CSV date parsing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)
            f.write("order_id,order_date,ship_date\n")
            f.write("1,2024-01-15,2024-01-17\n")
            f.write("2,2024-02-20,2024-02-22\n")

        try:
            # Read with date parsing
            table = Table.from_csv(temp_path, parse_dates=["order_date", "ship_date"])

            # Verify dates are parsed
            row0 = table.get("$0")
            assert isinstance(row0["order_date"], datetime)
            assert row0["order_date"].year == 2024
            assert row0["order_date"].month == 1
            assert row0["order_date"].day == 15
        finally:
            temp_path.unlink()

    def test_csv_skip_rows_and_max_rows(self):
        """Test skipping rows and limiting rows read."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)
            f.write("# Comment line\n")
            f.write("# Another comment\n")
            f.write("id,name\n")
            for i in range(10):
                f.write(f"{i},Name{i}\n")

        try:
            # Skip first 2 lines and read max 5 rows
            table = Table.from_csv(temp_path, skip_rows=2, max_rows=5)

            assert len(table) == 5
            assert table.get("$0.id") == 0
            assert table.get("$4.id") == 4
        finally:
            temp_path.unlink()

    def test_csv_with_index(self):
        """Test writing and reading CSV with row index."""
        # Create table with custom row keys
        table = Table()
        table.append({"name": "Alice", "age": 30}, custom_key="alice")
        table.append({"name": "Bob", "age": 25}, custom_key="bob")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write with index
            table.to_csv(temp_path, index=True)

            # Read back
            table2 = Table.from_csv(temp_path)

            # Verify index was written as column
            assert "_index" in table2.columns
            assert table2.get("$0._index") == "$alice"
            assert table2.get("$1._index") == "$bob"
        finally:
            temp_path.unlink()

    def test_csv_append_mode(self):
        """Test appending to existing CSV file."""
        data1 = [{"id": 1, "name": "Alice"}]
        data2 = [{"id": 2, "name": "Bob"}]

        table1 = Table(data1)
        table2 = Table(data2)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write first table
            table1.to_csv(temp_path)

            # Append second table
            table2.to_csv(temp_path, mode="a", header=False)

            # Read combined file
            combined = Table.from_csv(temp_path)

            assert len(combined) == 2
            assert combined.get("$0.name") == "Alice"
            assert combined.get("$1.name") == "Bob"
        finally:
            temp_path.unlink()

    def test_csv_with_nested_data(self):
        """Test CSV with nested dict/list data (JSON serialization)."""
        data = [
            {
                "id": 1,
                "metadata": {"type": "A", "count": 10},
                "tags": ["red", "blue"],
            },
            {
                "id": 2,
                "metadata": {"type": "B", "count": 20},
                "tags": ["green"],
            },
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write with nested data
            table.to_csv(temp_path)

            # Read back
            table2 = Table.from_csv(temp_path)

            # Nested data should be preserved as JSON
            row0 = table2.get("$0")
            assert isinstance(row0["metadata"], dict)
            assert row0["metadata"]["type"] == "A"
            assert isinstance(row0["tags"], list)
            assert "red" in row0["tags"]
        finally:
            temp_path.unlink()

    def test_csv_column_selection(self):
        """Test writing specific columns to CSV."""
        data = [
            {"id": 1, "name": "Alice", "age": 30, "city": "NYC"},
            {"id": 2, "name": "Bob", "age": 25, "city": "LA"},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write only specific columns
            table.to_csv(temp_path, columns=["id", "name"])

            # Read back
            table2 = Table.from_csv(temp_path)

            # Only selected columns should be present
            assert table2.columns == {"id", "name"}
            assert "age" not in table2.columns
            assert "city" not in table2.columns
        finally:
            temp_path.unlink()

    def test_csv_float_formatting(self):
        """Test float formatting in CSV output."""
        data = [
            {"id": 1, "value": 123.456789},
            {"id": 2, "value": 987.654321},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write with float formatting
            table.to_csv(temp_path, float_format="%.2f")

            # Read raw file to verify formatting
            with open(temp_path, "r") as f:
                lines = f.readlines()
                # Check that floats are formatted
                assert "123.46" in lines[1]  # Rounded
                assert "987.65" in lines[2]  # Rounded
        finally:
            temp_path.unlink()

    def test_csv_no_header(self):
        """Test CSV without header row."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)
            f.write("1,Alice,30\n")
            f.write("2,Bob,25\n")

        try:
            # Read without header
            table = Table.from_csv(
                temp_path, header=False, columns=["id", "name", "age"]
            )

            assert len(table) == 2
            assert table.get("$0.name") == "Alice"
            assert table.get("$1.age") == 25
        finally:
            temp_path.unlink()

    def test_csv_error_handling(self):
        """Test error handling for CSV operations."""
        table = Table([{"id": 1}])

        # Test file not found
        with pytest.raises(FileNotFoundError):
            Table.from_csv("/nonexistent/file.csv")

        # Test permission error simulation (we can't easily simulate this)
        # but the code handles it

        # Test malformed CSV handling
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)
            f.write("id,name\n")
            f.write("1,Alice\n")
            f.write("2\n")  # Missing column

        try:
            # Should handle gracefully by padding with None
            table = Table.from_csv(temp_path)
            assert len(table) == 2
            assert table.get("$1.name") is None
        finally:
            temp_path.unlink()


class TestTableParquet:
    """Test Parquet import/export functionality."""

    @pytest.fixture(autouse=True)
    def check_pyarrow(self):
        """Skip tests if pyarrow is not installed."""
        pytest.importorskip("pyarrow")

    def test_parquet_round_trip_basic(self):
        """Test basic Parquet write and read."""
        data = [
            {"id": 1, "name": "Alice", "age": 30, "score": 95.5},
            {"id": 2, "name": "Bob", "age": 25, "score": 88.0},
            {"id": 3, "name": "Charlie", "age": 35, "score": 92.3},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write to Parquet
            table.to_parquet(temp_path)

            # Read back
            table2 = Table.from_parquet(temp_path)

            # Verify data and types are preserved
            assert len(table2) == len(table)
            assert table2.columns == table.columns

            for i, (row1, row2) in enumerate(zip(table, table2)):
                assert row1["id"] == row2["id"]
                assert row1["name"] == row2["name"]
                assert row1["age"] == row2["age"]
                assert abs(row1["score"] - row2["score"]) < 0.001
        finally:
            temp_path.unlink()

    def test_parquet_with_nested_data(self):
        """Test Parquet with nested structures."""
        data = [
            {
                "id": 1,
                "user": {"name": "Alice", "email": "alice@example.com"},
                "tags": ["python", "data"],
                "scores": [95, 88, 92],
            },
            {
                "id": 2,
                "user": {"name": "Bob", "email": "bob@example.com"},
                "tags": ["java", "web"],
                "scores": [88, 90, 85],
            },
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write nested data
            table.to_parquet(temp_path)

            # Read back
            table2 = Table.from_parquet(temp_path)

            # Verify nested structures are preserved
            row0 = table2.get("$0")
            assert isinstance(row0["user"], dict)
            assert row0["user"]["name"] == "Alice"
            assert isinstance(row0["tags"], list)
            assert "python" in row0["tags"]
            assert isinstance(row0["scores"], list)
            assert row0["scores"][0] == 95
        finally:
            temp_path.unlink()

    def test_parquet_column_selection(self):
        """Test reading specific columns from Parquet."""
        data = [
            {"id": 1, "name": "Alice", "age": 30, "city": "NYC", "country": "USA"},
            {"id": 2, "name": "Bob", "age": 25, "city": "LA", "country": "USA"},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write all data
            table.to_parquet(temp_path)

            # Read only specific columns
            table2 = Table.from_parquet(temp_path, columns=["id", "name", "age"])

            # Verify only selected columns are present
            assert table2.columns == {"id", "name", "age"}
            assert "city" not in table2.columns
            assert "country" not in table2.columns
        finally:
            temp_path.unlink()

    def test_parquet_compression_options(self):
        """Test different compression options for Parquet."""
        data = [{"id": i, "value": i * 1.5} for i in range(100)]
        table = Table(data)

        compressions = ["snappy", "gzip", None]

        for compression in compressions:
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
                temp_path = Path(f.name)

            try:
                # Write with specific compression
                table.to_parquet(temp_path, compression=compression)

                # Read back
                table2 = Table.from_parquet(temp_path)

                # Verify data is preserved
                assert len(table2) == 100
                assert table2.get("$0.id") == 0
                assert table2.get("$99.id") == 99
            finally:
                temp_path.unlink()

    def test_parquet_with_null_values(self):
        """Test Parquet handling of null values."""
        data = [
            {"id": 1, "name": "Alice", "score": None},
            {"id": 2, "name": None, "score": 88.5},
            {"id": None, "name": "Charlie", "score": 92.0},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write with nulls
            table.to_parquet(temp_path)

            # Read back
            table2 = Table.from_parquet(temp_path)

            # Verify nulls are preserved
            assert table2.get("$0.score") is None
            assert table2.get("$1.name") is None
            assert table2.get("$2.id") is None
        finally:
            temp_path.unlink()

    def test_parquet_with_index(self):
        """Test Parquet with row index preservation."""
        # Create table with custom row keys
        table = Table()
        table.append({"name": "Alice", "age": 30}, custom_key="alice")
        table.append({"name": "Bob", "age": 25}, custom_key="bob")
        table.append({"name": "Charlie", "age": 35}, custom_key="charlie")

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write with index
            table.to_parquet(temp_path, index=True)

            # Read back
            table2 = Table.from_parquet(temp_path)

            # Verify index was written
            assert "_index" in table2.columns
            assert table2.get("$0._index") == "$alice"
            assert table2.get("$1._index") == "$bob"
            assert table2.get("$2._index") == "$charlie"
        finally:
            temp_path.unlink()

    def test_parquet_error_handling(self):
        """Test error handling for Parquet operations."""
        # Test file not found
        with pytest.raises(FileNotFoundError):
            Table.from_parquet("/nonexistent/file.parquet")

    def test_parquet_filters(self):
        """Test row filtering when reading Parquet."""
        data = [
            {"year": 2020, "month": 1, "sales": 100},
            {"year": 2020, "month": 2, "sales": 150},
            {"year": 2021, "month": 1, "sales": 200},
            {"year": 2021, "month": 2, "sales": 250},
            {"year": 2022, "month": 1, "sales": 300},
        ]
        table = Table(data)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write all data
            table.to_parquet(temp_path)

            # Read with filters
            table2 = Table.from_parquet(
                temp_path, filters=[("year", ">=", 2021), ("month", "==", 1)]
            )

            # Should only get 2021 and 2022 January data
            assert len(table2) == 2
            rows = list(table2)
            assert all(row["month"] == 1 for row in rows)
            assert all(row["year"] >= 2021 for row in rows)
        finally:
            temp_path.unlink()

    def test_parquet_partitioned_dataset(self):
        """Test writing partitioned Parquet dataset."""
        data = [
            {"year": 2020, "month": 1, "day": 1, "sales": 100},
            {"year": 2020, "month": 1, "day": 2, "sales": 150},
            {"year": 2020, "month": 2, "day": 1, "sales": 200},
            {"year": 2021, "month": 1, "day": 1, "sales": 250},
            {"year": 2021, "month": 2, "day": 1, "sales": 300},
        ]
        table = Table(data)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "partitioned_data"

            # Write partitioned dataset
            table.to_parquet(temp_path, partition_cols=["year", "month"])

            # Verify directory structure was created
            assert temp_path.exists()
            year_dirs = list(temp_path.glob("year=*"))
            assert len(year_dirs) == 2  # 2020 and 2021

            # Read back the partitioned dataset
            table2 = Table.from_parquet(temp_path)

            # Data should be preserved (though order might differ)
            assert len(table2) == len(table)
            all_sales = sorted([row["sales"] for row in table2])
            expected_sales = sorted([row["sales"] for row in table])
            assert all_sales == expected_sales


class TestTableIOIntegration:
    """Integration tests for Table I/O functionality."""

    def test_csv_to_parquet_conversion(self):
        """Test converting CSV to Parquet format."""
        pytest.importorskip("pyarrow")

        # Create CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as csv_file:
            csv_path = Path(csv_file.name)
            writer = csv.writer(csv_file)
            writer.writerow(["id", "name", "value"])
            writer.writerow([1, "Alice", 123.45])
            writer.writerow([2, "Bob", 678.90])

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as pq_file:
            parquet_path = Path(pq_file.name)

        try:
            # Read CSV and convert to Parquet
            table = Table.from_csv(csv_path, dtypes={"id": int, "value": float})
            table.to_parquet(parquet_path)

            # Read Parquet and verify
            table2 = Table.from_parquet(parquet_path)

            assert len(table2) == 2
            assert table2.get("$0.id") == 1
            assert table2.get("$0.name") == "Alice"
            assert abs(table2.get("$0.value") - 123.45) < 0.001
        finally:
            csv_path.unlink()
            parquet_path.unlink()

    def test_data_pipeline_example(self):
        """Test the data pipeline example from the spec."""
        pytest.importorskip("pyarrow")

        # Create sample data
        data = [
            {"id": 1, "name": "Alice", "status": "active", "value": 100},
            {"id": 2, "name": "Bob", "status": "inactive", "value": 200},
            {"id": 3, "name": "Charlie", "status": "active", "value": 300},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as csv_file:
            csv_path = Path(csv_file.name)
            writer = csv.DictWriter(
                csv_file, fieldnames=["id", "name", "status", "value"]
            )
            writer.writeheader()
            writer.writerows(data)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as pq_file:
            parquet_path = Path(pq_file.name)

        try:
            # Load, transform, and save
            table = Table.from_csv(csv_path)
            processed = (
                table.filter("status = 'active'")
                .map(lambda row: {**row, "value_doubled": int(row["value"]) * 2})
                .select("id, name, value_doubled")
            )
            processed.to_parquet(parquet_path)

            # Verify results
            result = Table.from_parquet(parquet_path)
            assert len(result) == 2  # Only active records
            assert set(result.columns) == {"id", "name", "value_doubled"}
            assert result.get("value_doubled") == [200, 600]  # 100*2, 300*2
        finally:
            csv_path.unlink()
            parquet_path.unlink()
