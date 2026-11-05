# F67 Manual Action Guide

## Required now

No portal action is required for the existing receipt. It is already uploaded, format accepted, and compatibility passed; full evaluation is still infrastructure pending.

1. Keep this computer awake and connected to the internet.
2. Keep the gateway Python process and `cloudflared.exe` tunnel running. The current Quick Tunnel depends on this computer.
3. Do not click **Withdraw**, **Save new revision**, or submit another ZIP while the current evaluation is outstanding.
4. Check the portal receipt status after the organizer retries infrastructure. The official receipt is `p-F67.04b40dbb-78a8-4c58-b3f8-90095310eaba`.

## If the gateway goes offline

Do not paste any token or provider key into ChatGPT. First check that the gateway service and Cloudflare tunnel are still running. If restarting them is necessary, use the existing gateway launch instructions in `gateway_service/DEPLOYMENT_GUIDE.md`, then run the portal’s generic **Check connection** only if the registered URL still matches the live tunnel URL.

If the Quick Tunnel URL changes, stop before changing the portal: a new URL requires a new gateway revision and may require a new source receipt. Ask for approval before changing the registered gateway or model. Do not enable paid hosting or billing without explicit approval.

## Keep private

- Provider API key.
- Restricted gateway bearer token.
- `gateway_service/.env` and any screenshots showing either secret.

Never include those values in a report, ZIP, GitHub commit, or chat message.
