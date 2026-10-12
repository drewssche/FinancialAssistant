import json
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, literal, select
from sqlalchemy.dialects import postgresql

from app.core.search import matches_search, search_rank, search_variants
from app.repositories.search import search_match

CASES = [
    ('Молоко', 'vjkjrj', True), ('Green', 'пкуут', True),
    ('ЗЕЛЁНЫЙ   чай', ' зеленый\tЧАЙ ', True),
    ('ёжик', '`;br', True), ('Хлеб', '[kt,', True),
    ('Женя', ':TYZ', True), ('Ёжик', '~;br', True),
    ('Vici 200 г', 'мшсш', True), ('Сыр 50%', '%', True),
    ('Сыр 50', '%', False), ('a_b', '_', True), ('acb', '_', False),
    ('Любой', ' ', True), ('Молоко', 'молка', False),
    ('Tom & Jerry <b>', '&', True), ('Foo\\bar', '\\', True),
]


@pytest.mark.parametrize('text,query,expected', CASES)
def test_search_python_and_sqlite_contract(text, query, expected):
    assert matches_search(text, query) is expected
    engine = create_engine('sqlite://')
    with engine.connect() as connection:
        assert bool(connection.scalar(select(search_match(literal(text), query)))) is expected
    engine.dispose()


def test_frontend_contract_and_safe_highlight():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the frontend contract test')
    result = subprocess.run([node, '-e', '''
      const fs = require('fs');
      global.window = {App: {core: {}}};
      eval(fs.readFileSync('static/js/app-search-utils.js', 'utf8'));
      eval(fs.readFileSync('static/js/app-renderers.js', 'utf8'));
      const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
      const search = window.App.search;
      const highlight = window.App.core.highlightText;
      process.stdout.write(JSON.stringify({
        cases: cases.map(([text, query]) => ({variants: search.variants(query), rank: search.rank(text, query), matches: search.matches(text, query)})),
        html: highlight('<img src=x onerror=alert(1)> МОЛОКО &', 'vjkjrj'),
        entity: highlight('Tom & Jerry', '&'),
        spaces: highlight('ЗелЁный   чай', 'зеленый чай'),
        order: search.prioritize([{name:'Молоко'}, {name:'vjkjrj'}], 'vjkjrj').map(item => item.name),
      }));
    '''], input=json.dumps(CASES), text=True, capture_output=True, check=True, cwd=Path(__file__).resolve().parents[2])
    data = json.loads(result.stdout)
    for (text, query, expected), actual in zip(CASES, data['cases']):
        assert actual == {'variants': list(search_variants(query)), 'rank': search_rank(text, query), 'matches': expected}
    assert data['html'] == '&lt;img src=x onerror=alert(1)&gt; <mark class="search-highlight">МОЛОКО</mark> &amp;'
    assert data['entity'] == 'Tom <mark class="search-highlight">&amp;</mark> Jerry'
    assert data['spaces'] == '<mark class="search-highlight">ЗелЁный   чай</mark>'
    assert data['order'] == ['vjkjrj', 'Молоко']


def test_postgres_query_uses_bound_literal_pattern():
    expression = select(search_match(literal('Молоко'), '50%_\\'))
    compiled = expression.compile(dialect=postgresql.dialect())
    assert 'regexp_replace' in str(compiled)
    assert '50%' not in str(compiled)
    assert '50/%/_\\' in compiled.params.values()
