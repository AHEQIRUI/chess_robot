#!/usr/bin/env python3
"""Stockfish HTTP API server - receives FEN, returns best move."""

import json
import sys
sys.path.insert(0, 'Stockfish-Python-API')
from stockfish_api import Stockfish

BIN = 'Stockfish-Python-API/stockfish_bin/stockfish'

def query(fen, depth=15):
    """Query Stockfish for best move given FEN."""
    try:
        with Stockfish(BIN, depth=depth) as engine:
            engine.set_fen(fen)
            move = engine.get_best_move(depth=depth)
            info = engine.get_move_info(depth=depth)
            return {
                'success': True,
                'best_move': move,
                'score': info.score,
                'depth': info.depth,
                'fen': fen
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    import http.server
    import socketserver
    import urllib.parse

    PORT = 8080

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == '/query':
                params = urllib.parse.parse_qs(parsed.query)
                fen = params.get('fen', [''])[0]
                depth = int(params.get('depth', ['15'])[0])
                if fen:
                    result = query(fen, depth)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': False, 'error': 'Missing fen'}).encode())
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<!DOCTYPE html><html><body>')
                self.wfile.write(b'<h1>Stockfish API</h1>')
                self.wfile.write(b'<p>GET /query?fen=...&depth=15</p>')
                self.wfile.write(b'</body></html>')

        def log_message(self, format, *args):
            print(f"[{self.address_string()}] {format % args}")

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Stockfish API server running on http://localhost:{PORT}")
        httpd.serve_forever()