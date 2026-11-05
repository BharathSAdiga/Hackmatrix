# F67 PORTAL REGISTRATION & NOMINATION GUIDE

**Project:** PARTSINTEL  
**Team:** F67 (Code Craft)  
**Portal Event Protocol:** `domainportal.v1`  
**Current Active Receipt:** `r-F67.0fcfcba0-010c-4f59-882b-a75f34c48939` (Revision 6)  

---

## 1. Portal Fields & Exact Values

When registering or updating gateway credentials in the official competition portal:

| Portal Form Field | Exact Value to Enter | Notes |
|---|---|---|
| **Gateway Endpoint URL** | `https://championships-nurse-temple-indexed.trycloudflare.com/gateway` | Standard Port 443 HTTPS |
| **Restricted Bearer Token** | `kNgcniuiLdfRJjTYBpLqraNGgENrKw_0W-Jh0wSthhQ` | Must match `TEAM_GATEWAY_TOKEN` |
| **Model Name** | `qwen/qwen3.8-27b` | Groq Cloud active model |
| **Submission File** | `CodeCraft_PARTSINTEL_FINAL.zip` *(or `PARTSINTEL_FINAL.zip`)* | SHA256: `59593240a3423f03...` |

---

## 2. Event Rules on Gateway Revisions & Receipts

Per official `EVENT_RULES.md` and `GATEWAY.md`:
1. **Gateway Revision Coupling:**
   > *"Gateway/model changes need a new source receipt with a new endpoint revision. Preserve submitted revisions/tokens through 19:45 IST and until announced final testing completion if the organizer extends testing."*
2. **Impact of Changing Configuration:**
   - Registering a new gateway URL advances the gateway revision number (e.g. Revision 6 -> Revision 7).
   - Any outstanding source receipt tied to the earlier revision must either be re-tested or re-uploaded to associate with the new revision.
   - **Recommendation:** Do NOT change the registered gateway URL while full grading is queued / pending.

---

## 3. Critical Platform Warnings

> [!CAUTION]
> **DO NOT CLICK "WITHDRAW" ON THE PORTAL:**
> - The portal explicitly states:
>   > *"Before final cutoff, you may withdraw checking, queued or infrastructure-failed work; a manual withdrawal without a confirmed compatibility failure keeps the attempt used."*
> - Your receipt has already achieved **`Compatibility passed`**.
> - Clicking "Withdraw" will **permanently burn 1 of your 4 allowed attempts** without refunding it, leaving your submission with zero score.
> - Simply click the **"Refresh"** button at the top-right of the portal page every 1–2 minutes while the organizer's background grading pod processes the queue.

