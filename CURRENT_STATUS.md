# Current Status

## Completed

- Backend skeleton is implemented with FastAPI.
- Database models are implemented for customers, addresses, conversations, carts, orders, messages, and menu items.
- Chaihouse menu is seeded for the POC.
- WhatsApp webhook verification and receive routes are implemented.
- Google ADK runtime is integrated with a real `Runner`, a custom ADK agent, and persistent ADK session storage.
- The ADK layer now uses a main Chaihouse agent, routed workflow sub-agents, and structured business function-tools with documented inputs and flags.
- Ordering flow is implemented:
  - greeting
  - menu sending
  - cart building
  - minimum order validation
  - address capture
  - order confirmation
- Minimum online order value is enforced at Rs 500.
- Customer profile and default address can be stored and reused.
- Orders are saved in the database.
- Staff dashboard is implemented for viewing and updating order status.
- Local scripts are included for dev startup, conversation simulation, and sample webhook testing.
- Sample WhatsApp webhook payloads are included.

## Pending

- Replace placeholder allowed block codes with the real Green Heritage block codes.
- Add real WhatsApp Cloud API credentials in `.env`.
- Deploy the backend to a public HTTPS host for live webhook use.
- Configure Meta webhook verification and production callback URL.
- Integrate with Petpooja in a later phase.
- Optionally upgrade the current deterministic ADK custom agent to a Gemini-powered `LlmAgent` later.

## Local Testing

### Option 1: Simulated conversation

```powershell
python scripts\run_test_conversation.py
```

### Option 2: Run the backend locally

```powershell
.\scripts\start_dev.ps1
```

Then open:

- Dashboard: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`
- Menu API: `http://127.0.0.1:8000/api/menu`

### Option 3: Send sample webhook payloads

```powershell
python scripts\send_sample_webhook.py --file samples\whatsapp_inbound_hi.json
python scripts\send_sample_webhook.py --file samples\whatsapp_inbound_order.json
```

## Notes

- Without live Meta credentials, outbound WhatsApp replies are stubbed and logged locally.
- ADK is already integrated in the runtime. The remaining ADK-related work is optional model-driven enhancement, not base runtime setup.
- The POC is ready for local demo use now.
