# F67 GATEWAY RUNTIME & OPERATIONS MANUAL

**Project:** PARTSINTEL  
**Team:** F67 (Code Craft)  
**Host Platform:** Windows 11 (AMD64)  
**Target Ingress:** `127.0.0.1:8080` (HTTP) -> `Port 443` (Cloudflare Tunnel HTTPS)  

---

## 1. Gateway Process Management

The gateway runs as a background process pairing the Python HTTP reverse proxy with Cloudflare's tunnel agent.

### Current Process Status
- **Managed Task ID:** `task-471`
- **Script Executed:** `python gateway_service/launch_live_tunnel.py`
- **Uptime:** Continuously active for >1 hour 40 minutes.
- **Port:** `127.0.0.1:8080` (TCP loopback).

### Verifying Gateway Health
Run this one-line health check from any terminal:
```powershell
Invoke-RestMethod -Uri "https://championships-nurse-temple-indexed.trycloudflare.com/gateway" -Method Post -Headers @{"Authorization"="Bearer kNgcniuiLdfRJjTYBpLqraNGgENrKw_0W-Jh0wSthhQ"; "Content-Type"="application/json"} -Body '{"messages":[{"role":"user","content":"ping"}],"max_output_tokens":32}'
```

---

## 2. Host Computer Uptime Requirements

> [!IMPORTANT]
> Because the gateway runs on your local machine via Cloudflare Tunnel, **the computer must remain awake and connected to the internet during evaluation**.

### Mandatory Host Settings:
1. **Power & Sleep:**
   - Open Windows **Settings -> Power & Battery**.
   - Under **Screen and sleep**, set:
     - *"When plugged in, put my device to sleep after"*: **Never**.
2. **Network Connection:**
   - Keep Wi-Fi or Ethernet continuously connected.
   - Do not close laptop lid if closing suspends the machine.

---

## 3. Permanent Windows Service Setup (Optional Unattended Mode)

To make the gateway run automatically on Windows startup without requiring any open terminal window:

### Using Windows Task Scheduler:
1. Open **Task Scheduler** (`taskschd.msc`).
2. Click **Create Task** (Name: `PARTSINTEL_GATEWAY_DAEMON`).
3. Under **General**: Select *"Run whether user is logged on or not"*, check *"Run with highest privileges"*.
4. Under **Triggers**: Click **New** -> *"At startup"*.
5. Under **Actions**: Click **New** -> Action: *"Start a program"*:
   - Program: `C:\Users\bhara\AppData\Local\Programs\Python\Python313\python.exe`
   - Arguments: `D:\Ksit Hackathon\gateway_service\launch_live_tunnel.py`
   - Start in: `D:\Ksit Hackathon`
6. Under **Conditions**: Uncheck *"Stop if the computer switches to battery power"*.
7. Click **OK** to save.
