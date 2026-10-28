"""Jedna instancja aplikacji. Uruchom: python app.py 8001"""
import os
import sys

from flask import Flask, jsonify, request
from valkey.exceptions import ValkeyError

import limiter

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8001"))

app = Flask(__name__)


@app.get("/check")
def check():
    client_id = request.args.get("client")
    algo = request.args.get("algo", "sliding")

    if not client_id:
        return jsonify(error="brak parametru client"), 400
    fn = limiter.ALGORITHMS.get(algo)
    if fn is None:
        return jsonify(error=f"nieznany algorytm: {algo}"), 400

    try:
        allowed = fn(client_id)
    except ValkeyError as exc:
        # Valkey niedostepny: zwracamy 503, zeby awarie byly widoczne w pomiarach
        return jsonify(error=type(exc).__name__, instance=PORT, algo=algo), 503

    status = 200 if allowed else 429
    return jsonify(allowed=allowed, instance=PORT, algo=algo), status


@app.get("/health")
def health():
    return jsonify(instance=PORT, status="ok")


if __name__ == "__main__":
    # threaded=True: kazde zadanie w osobnym watku, jak w typowym serwerze aplikacyjnym
    app.run(host="127.0.0.1", port=PORT, threaded=True)
