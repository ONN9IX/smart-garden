"""Offline structural smoke check for imported n8n workflow (no credentials)."""
from pathlib import Path
import json

path = Path(__file__).resolve().parents[1] / 'n8n' / 'smart-garden-dispatcher.json'
data = json.loads(path.read_text(encoding='utf-8'))
assert data['active'] is False
assert data['settings']['executionOrder'] == 'v1'
assert len(data['nodes']) == 5
ids = [node['name'] for node in data['nodes']]
assert len(ids) == len(set(ids))
assert any(node['type'] == 'n8n-nodes-base.scheduleTrigger' for node in data['nodes'])
assert any(node['type'] == 'n8n-nodes-base.telegram' for node in data['nodes'])
assert not any('secret' in str(node).lower() for node in data['nodes'])
print('n8n workflow structural checks: PASS')
