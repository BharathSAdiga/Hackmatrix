# F67 CLOUDFLARE TUNNEL INFRASTRUCTURE & DOMAIN AUDIT

**Project:** PARTSINTEL  
**Team:** F67 (Code Craft)  
**Target Tunnel:** `PARTSINTEL-PRODUCTION`  
**Current Live Endpoint:** `https://championships-nurse-temple-indexed.trycloudflare.com/gateway` (Port 443 HTTPS)  

---

## 1. Domain & Cloudflare Authentication Audit

As required by **Phase 5 of the Master Mission**, we performed an audit to determine whether an active Cloudflare domain or certificate exists on this machine:

### Verification Command Executed:
```powershell
& "D:\Ksit Hackathon\gateway_service\cloudflared.exe" tunnel list
```

### Result:
```text
2026-11-05T10:50:42Z ERR Cannot determine default origin certificate path.
No file cert.pem in [~/.cloudflared ~/.cloudflare-warp ~/cloudflare-warp].
Error locating origin cert: client didn't specify origincert path
```

### Audit Finding:
1. **No Cloudflare Origin Certificate (`cert.pem`):** The local CLI has not been logged in to a Cloudflare account via `cloudflared tunnel login`.
2. **Missing Prerequisite:** Cloudflare Named Tunnels (e.g. `PARTSINTEL-PRODUCTION` with a permanent custom hostname) strictly require:
   - An active Cloudflare account.
   - At least one registered domain / DNS zone managed in that Cloudflare account (e.g. `yourdomain.com`).
   - Execution of `cloudflared tunnel login` to download the account certificate `cert.pem`.

---

## 2. Options for Permanent Domain & Named Tunnel

Per competition guidelines, **no purchase is made without explicit user approval** (Budget limit: ₹1,000).

### Option 1: Continue Using Active Cloudflare Quick Tunnel (Recommended — ₹0 / Free)
- **Current URL:** `https://championships-nurse-temple-indexed.trycloudflare.com/gateway`
- **Cost:** **₹0.00**
- **HTTPS & TLS:** TLS 1.3 on standard Port 443, signed by Google Trust Services.
- **Current Uptime:** Active and healthy for >1 hour 35 minutes via daemon `task-471`.
- **Portal Compatibility:** Already registered as Revision 5 / Revision 6.
- **Risk:** If the local host process is closed or the tunnel agent restarts, Cloudflare assigns a new random subdomain.

### Option 2: Deploy Named Tunnel (`PARTSINTEL-PRODUCTION`) with a Custom Domain
If you own or wish to acquire a permanent domain:
- **Cheapest Domain Options:**
  - Cloudflare Registrar / Namecheap: `.xyz`, `.site`, or `.top` TLDs typically cost **\$0.99 to \$2.00 (₹85 – ₹170)** for 1 year (well within the ₹1,000 budget limit).
  - Free options: If you already own an existing domain on Cloudflare, you can add a subdomain like `f67-gateway.yourdomain.com` at **₹0 cost**.
- **Setup Procedure:**
  1. User runs: `& "D:\Ksit Hackathon\gateway_service\cloudflared.exe" tunnel login`
  2. Browser opens Cloudflare dashboard; select the domain to authorize.
  3. Run: `& "D:\Ksit Hackathon\gateway_service\cloudflared.exe" tunnel create PARTSINTEL-PRODUCTION`
  4. Create `~/.cloudflared/config.yml`:
     ```yaml
     tunnel: <TUNNEL_UUID>
     credentials-file: C:\Users\bhara\.cloudflared\<TUNNEL_UUID>.json
     ingress:
       - hostname: gateway.yourdomain.com
         service: http://127.0.0.1:8080
       - service: http_status:404
     ```
  5. Route DNS: `& "D:\Ksit Hackathon\gateway_service\cloudflared.exe" tunnel route dns PARTSINTEL-PRODUCTION gateway.yourdomain.com`
  6. Install as Windows Service:
     ```powershell
     & "D:\Ksit Hackathon\gateway_service\cloudflared.exe" service install
     Start-Service cloudflared
     ```

---

## 3. Operational Policy

> [!IMPORTANT]
> To protect the official submission that is currently pending evaluation, **we are keeping the existing Quick Tunnel operational and undisturbed**.
> Do not kill task `task-471` until full grading has finished or until a permanent domain is explicitly approved and deployed.
