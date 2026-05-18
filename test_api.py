from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_settings_endpoint():
    r = client.get('/api/settings')
    assert r.status_code == 200
    data = r.json()
    assert 'ollama_url' in data


def test_tones_endpoint():
    r = client.get('/api/tones')
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_providers_endpoint():
    r = client.get('/api/providers')
    assert r.status_code == 200
    assert 'openai' in r.json()


def test_prompt_limit():
    long_prompt = 'x' * 50000
    r = client.post('/api/optimize', json={'prompt': long_prompt})
    assert r.status_code in [400, 413, 422, 503]
