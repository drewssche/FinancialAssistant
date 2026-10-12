"""Serve the frontend fixture with room for parallel JS/CSS requests.

The app's manifest loads over 100 assets concurrently. The default small
listen backlog can reset connections in Chromium and make UI checks flaky.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer, test
import argparse


class FixtureServer(ThreadingHTTPServer):
    request_queue_size = 128


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int)
    parser.add_argument('--bind', default='127.0.0.1')
    args = parser.parse_args()
    test(HandlerClass=SimpleHTTPRequestHandler, ServerClass=FixtureServer,
         port=args.port, bind=args.bind)
