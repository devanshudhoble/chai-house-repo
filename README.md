# Chaihouse WhatsApp Ordering POC

FastAPI-based proof of concept for WhatsApp ordering with:

- WhatsApp webhook endpoints
- real Google ADK runtime integration
- SQLite persistence
- staff dashboard
- Green Heritage address validation
- Rs 500 minimum online order rule
- Chaihouse real menu seeded for the POC

## What This POC Does

1. Receives inbound WhatsApp messages through a webhook.
2. Creates or loads the customer and active conversation.
3. Runs the Chaihouse ordering flow through a real Google ADK `Runner` with persistent ADK session storage:
   - root `ChaihouseMainAgent` routes by conversation step
   - workflow sub-agents handle welcome, cart, details, and confirmation
   - structured business function-tools return typed payloads for parsing and validation
   - greets the customer
   - sends the menu
   - builds a cart
   - enforces minimum order value
   - collects delivery details
   - saves the order
4. Shows confirmed orders in a staff dashboard.

## Project Layout

```text
app/
  agents/
  routes/
  services/
  static/
  templates/
  config.py
  db.py
  main.py
  models.py
  seed.py
```

Tracking docs:

- `CURRENT_STATUS.md` for completed work and local test notes
- `PENDING.md` for remaining live-integration work

## Local Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

PowerShell shortcut:

```powershell
.\scripts\start_dev.ps1
```

Open:

- Dashboard: `http://127.0.0.1:8000/`
- WhatsApp webhook verify + receive: `http://127.0.0.1:8000/webhooks/whatsapp`
- Health: `http://127.0.0.1:8000/health`
- Menu API: `http://127.0.0.1:8000/api/menu`
- Runtime settings API: `http://127.0.0.1:8000/api/settings`

## Environment Variables

Copy `.env.example` to `.env` and edit values as needed:

```env
DATABASE_URL=sqlite:///./chaihouse.db
ADK_SESSION_DATABASE_URL=sqlite+aiosqlite:///./chaihouse.db
WHATSAPP_VERIFY_TOKEN=chaihouse-verify-token
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
BUSINESS_NAME=Chaihouse Cafe
PROPERTY_NAME=Green Heritage
MIN_ORDER_VALUE=500
ALLOWED_BLOCKS=AA,AB,AC,BA,BB,BC,CA,CB
```

If `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` are not set, outbound replies are stubbed and only logged locally.

## Test The POC Without WhatsApp

Option 1: run the internal conversation simulator:

```bash
python scripts/run_test_conversation.py
```

Option 2: send a sample webhook payload to the POST endpoint:

```json
{
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "id": "wamid.test1",
                "from": "919876543210",
                "type": "text",
                "text": { "body": "Hi" }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

Ready-made sample payloads are included in `samples/`.

Example:

```bash
python scripts/send_sample_webhook.py --file samples/whatsapp_inbound_hi.json
python scripts/send_sample_webhook.py --file samples/whatsapp_inbound_order.json
```

Then continue with messages like:

- `2 masala chai, 4 samosa, 2 plain maggi, 2 nimbu pani`
- `Rahul`
- `9876543210`
- `AB`
- `402`
- `YES`

## Notes

- The repo is now ADK-backed. Inbound WhatsApp turns run through a real Google ADK `Runner`.
- The current ADK agent is a custom deterministic `BaseAgent`, so the POC works locally without Gemini credentials.
- If you later want a model-driven version, this ADK runtime can be upgraded to an `LlmAgent` without replacing the webhook, DB, or dashboard layers.
- The current allowed block list is configurable through `.env`.

## WhatsApp Cloud API Live Hookup

When you are ready to move from local stub mode to real WhatsApp:

1. Create and configure a Meta app with WhatsApp Business Platform access.
2. Get:
   - `WHATSAPP_ACCESS_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - a webhook verify token you control
3. Put those values into `.env`.
4. Deploy the backend to a public HTTPS URL.
5. Set the webhook URL in Meta:
   - `GET /webhooks/whatsapp` for verification
   - `POST /webhooks/whatsapp` for inbound messages
6. Verify the webhook using `WHATSAPP_VERIFY_TOKEN`.
7. Send a test message from a customer/test number.

Once those credentials are set, the app stops stubbing outbound messages and sends them through the Cloud API automatically.
