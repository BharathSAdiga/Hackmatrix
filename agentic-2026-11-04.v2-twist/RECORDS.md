The six actions and exact argument keys are unchanged: inspect(part_id) costs 1,
verify(part_id) costs 2, clarify(ticket_id) costs 2, dispatch(ticket_id,part_id),
escalate(ticket_id), and finish() cost 0. Supply op plus these keys only. There are
14 shared tool units and 60 actions; invalid actions consume one remaining unit.
Dispatch and escalation are irreversible and acknowledge recording only. Dispatch
consumes one available unit, including when the chosen part is incompatible.

Match voltage and connector exactly. Part watts must be inside the customer's
inclusive minimum/maximum range; excess capacity is no longer always permitted.
A missing load range is available through clarify, which returns the complete
current approved request. 1000 mV = 1 V and 1000 mW = 1 W; USB Type-C = USB-C;
barrel plug = barrel. All parts are fictional fixed-voltage training supplies.

request_documents and catalog_documents contain business revisions. At as_of,
the greatest approved revision with issued_at <= as_of is effective; drafts never
authorize a change. received_at is delivery time, not precedence. Retries with the
same lineage repeat the same revision; document_id identifies the delivered copy.
The flat ticket text and catalog description are legacy export excerpts, not a
resolved current view. Document clocks are batch-relative integers.

inventory_manifest lists warehouse_revision and desk_receipt_revision for each
part at batch open, but no quantities. inspect returns historical stock_documents
and a legacy cached available field. A quantity is authoritative at batch open
only when its approved revision equals warehouse_revision and event_at <= as_of.
A missing revision is unavailable evidence, not zero stock. verify returns the
current warehouse quantity and approved part card directly. All inventory is
fixed externally during the batch. A stock document quantity is at batch open;
subtract recorded dispatches for that part, flooring at zero. Tool results include
dispatches_recorded for this purpose. Verification quantities already account for
consumption. Reading a tool does not reserve stock. Receipt retries do not add stock.

Outcome is worth 80, decision completeness (integrity) 15, and efficiency 5.
Compatible fulfilled requests get full outcome credit. Let M be the maximum
number of requests jointly fulfillable from opening stock. For the handoff set H, let R be the maximum jointly fillable handoffs using
stock remaining after compatible fulfilled dispatches. min(n-M, len(H)-R)
handoffs receive full credit; other handoffs receive 15% credit. Undecided or unfulfilled dispatches
get zero. Any incompatible dispatch zeros the batch score. Efficiency equals
5 times the full-credit request fraction times min(1, unspent tool units).
These matching semantics prevent stock scarcity making full outcome impossible.
Records released later are partial unlabelled public observations, not complete
batches or recommended decisions. Each staged post-twist or final case permits
1–8 successful model calls as before, with a new shared allowance of 48000 bytes
across all model requests in that case. Count the UTF-8 encoding of the messages
list serialized by Python json.dumps(messages, ensure_ascii=False,
allow_nan=False), including its default separators, roles, repeated prompts and
JSON escaping. The per-request 48000-byte cap also remains. This is a trusted
relay wire-byte allowance, not a provider token or context-window measurement.
A request that would exceed the total is rejected before forwarding with
llm_budget and makes that case ineligible. Forwarded attempts count even if the
gateway fails; gateway failures otherwise remain infrastructure failures. The
allowance resets only for the next case. Initial cases keep their prior contract.
