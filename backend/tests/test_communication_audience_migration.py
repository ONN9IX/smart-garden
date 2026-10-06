"""Communication audience migration keeps canonical history on the all audience."""

from sqlalchemy import inspect

from app.db.session import engine


def test_0013_communication_audience_is_current(migrations):
    with engine.connect() as connection:
        columns = {item["name"] for item in inspect(connection).get_columns("communication_threads")}
        indexes = {item["name"]: item for item in inspect(connection).get_indexes("communication_threads")}
    assert "audience" in columns
    assert indexes["uq_communication_threads_group"]["column_names"] == ["group_id", "audience"]
