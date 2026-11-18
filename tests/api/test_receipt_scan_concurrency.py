"""Race independent request sessions at the database's unique key."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.deps import get_current_user_id
from app.db.base import Base
from app.db.models import ActivityEvent, Operation, OperationItemPrice, OperationReceiptItem, ReceiptScanSubmission, User
from app.db.session import get_db
from app.main import app
from tests.api.test_receipt_scan_storage_api import reviewed_expense


@pytest.mark.parametrize('database', ['sqlite', 'postgresql'])
def test_two_requests_create_one_expense_and_one_set_of_side_effects(database, tmp_path):
    schema_engine = None
    if database == 'postgresql':
        url = os.getenv('MIGRATION_TEST_DATABASE_URL')
        if not url:
            pytest.skip('Requires a disposable PostgreSQL database')
        assert 'migration_test' in url
        schema = 'receipt_scan_' + uuid4().hex
        schema_engine = create_engine(url)
        with schema_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(url, connect_args={'options': '-csearch_path=' + schema})
    else:
        engine = create_engine('sqlite:///' + str(tmp_path / 'receipts.db'))
    sessions = sessionmaker(engine)
    barrier = Barrier(2, timeout=10)
    def get_session():
        with sessions() as session:
            yield session

    try:
        Base.metadata.create_all(engine)
        with sessions.begin() as session:
            session.add(User(id=1, display_name='Тест', status='active'))

        @event.listens_for(engine, 'before_cursor_execute')
        def meet_at_insert(conn, cursor, statement, parameters, context, many):
            if statement.startswith('INSERT INTO receipt_scan_submissions'):
                barrier.wait()

        app.dependency_overrides[get_db] = get_session
        app.dependency_overrides[get_current_user_id] = lambda: 1
        headers = {'Idempotency-Key': str(uuid4())}
        payload = reviewed_expense()
        with TestClient(app) as client, ThreadPoolExecutor(2) as workers:
            requests = [workers.submit(client.post, '/api/v1/operations', json=payload, headers=headers) for _ in range(2)]
            responses = [req.result(timeout=25) for req in requests]
        assert [r.status_code for r in responses] == [201, 201], [r.text for r in responses]
        assert responses[0].json()['id'] == responses[1].json()['id']
        with sessions() as session:
            for model in (Operation, OperationReceiptItem, OperationItemPrice, ReceiptScanSubmission):
                assert session.scalar(select(func.count()).select_from(model)) == 1
            assert session.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.entity_type == 'operation')) == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user_id, None)
        engine.dispose()
        if schema_engine is not None:
            with schema_engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            schema_engine.dispose()
