"""Exercise every native provider route over loopback HTTP without inference."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import time
from urllib.error import HTTPError, URLError

import pytest

from llm_reservoir_agent.configured_backend import http_json_transport
from tests.test_daily_provider_matrix import _backend, _observation, _reply


@contextmanager
def local_provider(provider, outcome):
    """Serve a handwritten native envelope and retain received requests in memory."""
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            calls.append((self.path, payload))
            if outcome == 'timeout':
                time.sleep(0.2)
            body = json.dumps(_reply(provider)).encode('utf-8')
            self.send_response(503 if outcome == 'http_error' else 200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except ConnectionError:
                # Expected only when the timeout client has already closed.
                if outcome != 'timeout':
                    raise
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = False  # server_close joins every bounded request handler.
    worker = Thread(target=server.serve_forever, kwargs={'poll_interval':0.01}, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', calls
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        assert not worker.is_alive(), 'Local fixture server failed to stop'


@pytest.mark.parametrize('provider,path', [
    ('ollama','/api/chat'), ('openai_compatible','/chat/completions'),
    ('openai','/responses'), ('anthropic','/v1/messages'),
    ('gemini','/models/fixture-model:generateContent'),
])
@pytest.mark.parametrize('outcome', ['success','http_error','timeout'])
def test_five_native_routes_use_local_http_once(provider, path, outcome):
    with local_provider(provider, outcome) as (url, calls):
        backend = _backend(provider, http_json_transport, base_url=url,
                           timeout_seconds=0.05 if outcome=='timeout' else 2)
        if outcome == 'success':
            assert backend.decide(_observation()).release_cms == 2.5
            assert backend.latest_trace['usage']
        else:
            error = HTTPError if outcome=='http_error' else (TimeoutError, URLError)
            with pytest.raises(error):
                backend.decide(_observation())
        assert len(calls) == 1, 'No retry was configured'
        assert calls[0][0] == path
        assert isinstance(calls[0][1], dict)
        assert backend.network_calls == 1
