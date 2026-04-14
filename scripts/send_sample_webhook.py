import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a sample WhatsApp webhook payload to the local POC.")
    parser.add_argument(
        "--file",
        default="samples/whatsapp_inbound_hi.json",
        help="Path to sample JSON payload",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/webhooks/whatsapp",
        help="Webhook URL",
    )
    args = parser.parse_args()

    payload_path = Path(args.file)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    response = httpx.post(args.url, json=payload, timeout=30.0)
    print("Status:", response.status_code)
    print(response.text)


if __name__ == "__main__":
    main()
