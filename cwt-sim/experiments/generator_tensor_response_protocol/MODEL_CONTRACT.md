# Generator-tensor response protocol — pre-access contract

This isolated adapter is source-only. It does not claim that any reserved
response has historically remained unopened. The current reservation status is
`RESERVED_BY_PROCESS_ATTESTATION / NOT_CRYPTOGRAPHICALLY_PROVEN_UNOPENED`.

Publication chronology is path-closed: the source commit adds exactly the
fourteen reviewed material files, its child adds only the sibling SOURCE_LOCK,
and each phase-authorization commit adds only its one canonical authority
record. Replace-object rewriting and worktree fallback are refused.

## Immutable chronology

- Predictor source: commit `c140709179719eb6ed827097e1aa96c26acf93f6`,
  tree `28caa6b381f52cc39d75585ace08c823134cbeff`.
- Predictor metadata lock: commit
  `1f4cd82e9e44faea22ab3b12464042a0678b3abd`, raw SHA-256
  `9b9f2c112581f575f35cf599afd2f708bc9c241eed2512ef166ed62293757cd8`.
- Response producer SOURCE_LOCK raw SHA-256
  `d513614df4f375a756b7cb593cd47ac729b4a702dcea5448be69cdfa9e3da3a9`.

Producer sources are inspected as text and AST during the source phase. They are
not imported. The future real broker requires a clean process and binds exact
module origins, raw source bytes, code compiled from those bytes, canonical
function ASTs, transitive call graphs, blobs, qualnames, and signatures before
its first lazy import. A preloaded producer module is refused.

## Target and call discipline

The target is literally

`DeltaF(c) = direct_response_curl(build_branch_bundle(c, r=1/20), orientation=+1) - direct_response_curl(build_branch_bundle(c, r=0), orientation=+1)`.

The component order is `(F_d_t, F_t_b, F_b_d)`. At each radius the direct
stationary/Drazin curl must exactly equal the independently derived FCS
normal-connection curl before subtraction. Calibration makes exactly twelve
top-level producer sample calls: radius `1/20`, then radius `0`, center-major
over `A1` through `A6`. Inputs and outputs are exact `Fraction` objects. There
is no normalization, sign flip, intercept, weighting, regularization,
tolerance, or fallback.

Before subtraction and fitting, each raw producer curvature is pulled into the
predictor's normalized chart with `(D_b,D_d,D_t)=(1/50,1/50,1/6)`.
Components `(F_d_t,F_t_b,F_b_d)` are multiplied respectively by
`(D_d*D_t,D_t*D_b,D_b*D_d)=(1/300,1/300,1/2500)`. Both raw and normalized
exact values remain in the in-memory broker record. No extra factor or
orientation averaging is permitted. The producer bindings are explicitly
`B=j R X`, `F=dB`, and the separately computed FCS
`F=-partial_q(dA)`; direct and FCS objects must be distinct and exact-equal.

## Lanes

1. The geometry/call-plan lane imports only the locked count-blind predictor.
   It never receives a producer capability or response.
2. The broker lane contains the sole lazy producer import. It receives no
   geometry basis, coefficients, or predictions.
3. The fit/prediction lane has no producer capability. It solves
   `k=(X^T X)^-1 X^T y`, requires exact rank three and all eighteen exact
   residuals zero, and otherwise stops.

Even an exact passing fit is classified `DEGENERATE_NONINFORMATIVE_FIT` and
stops before prediction commitment if `k=(0,0,0)` or the already locked
heldout scalar prediction is exactly zero.

After calibration PASS, coefficients, the full fit provenance, both complete
confirmation vectors, and the heldout scalar projection for area `(1,-1,3)`
are prepared as one canonical record. Confirmation remains impossible until a
fresh external authority process commits that exact record in the immutable V
authorization commit. A payload boolean is never evidence of prior locking.
V1 and V2 responses are obtained atomically. Heldout access is impossible
until both pass, and its broker interface returns only the scalar projection.

## One-way state and publication

The mandatory prefix is
`PREDICTOR_LOCKED -> ADAPTER_SOURCE_LOCKED -> CAL_AUTHORIZED -> CAL_ACCESSED -> CAL_RESULT_COMMITTED -> CAL_PASS|CAL_FAIL|CAL_INDETERMINATE`.
Only a committed CAL PASS may authorize prediction commitment. The exact fit,
prediction, response-result, and reviewed outcome must then be committed before
a separate V authorization commit can exist. H analogously requires an atomic
V1/V2 result and a separately reviewed, committed V PASS. Each authority commit
has exactly one parent. Each outcome commit has exactly two added paths: the
canonical complete phase result and its canonical external outcome. Result
bytes bind the authority record and fixed request IDs; CAL vectors bind the fit
observations, V vectors bind both locked predictions, and H binds only the
locked scalar projection.

The authoritative attempt/outcome ledger is an explicit absolute directory
managed by the outer orchestrator, outside every disposable detached checkout.
It has no default or worktree fallback. Before launching a child, the outer
orchestrator provisions and verifies an existing ordinary, link/reparse-free
directory and refuses launch if the exact key for the phase-authority commit
OID, session, phase, and sequence already exists. The fresh child, not the
outer launcher, then atomically creates that key with exclusive-create
semantics before importing the producer. Every fresh checkout for the same
authority uses that same durable store, so a crash after the first access cannot
be retried by creating a new checkout. Checkout-local ledger paths are
diagnostic only and never grant a later phase, even when a same-user process
precreates an exact PASS-shaped file. Later authority derives only from the
reviewed Git chronology and exact committed result/outcome blobs.

This durable no-retry property is process-controlled by the trusted outer
orchestrator; it is not cryptographic protection against same-user or
administrator tampering with the ledger root. The incident/outcome evidence
must later be independently committed and published before any next-phase
authorization is reviewed.

There is no authoritative importable per-sample broker API. Real response
access is authorized only by an outer trusted orchestrator. It must materialize
a fresh detached checkout from the exact adapter-lock/phase-authority Git
objects, pass explicit absolute Git directory, index, and worktree bindings,
and invoke the reviewed hidden whole-phase CLI with trusted absolute Git and
Python executables in a fresh `python -I -B` process. The detached worktree has
no `.git`, link/reparse entry, `__pycache__`, or `*.pyc` anywhere in the adapter,
predictor, or response-producer import roots. `PYTHONPYCACHEPREFIX` names a
verified-empty external temporary directory; user site, `PYTHONPATH`, startup,
and bytecode writes are disabled. The outer orchestrator independently verifies
the complete result and cache-free checkout after the child exits.

That child accepts only one authority commit OID,
rederives the fixed phase call plan, consumes the durable start marker before
importing the producer, authenticates the exact reviewed callables and their
transitive helpers (including their live code/defaults/closures), executes the
entire phase batch, independently reconstructs direct and FCS curls from their
separate derivative matrices, transactionally publishes
one complete result, and exits. It cannot advance the state itself. A later
phase remains impossible until an external review commits the result and
outcome and separately commits the next authorization. Any producer exception
or partial batch after first access creates a sanitized terminal incident and
cannot be retried or expose provider output.

The child's argv, module globals, and import-time guards are defense in depth;
they do not prove that the OS created a fresh process. Arbitrary mutation of
process memory, syscall wrappers, interpreter/Git binaries, or administrator
state is outside this analytic protocol's threat model. Only the external
detached-launch and post-verification workflow is the claimed publication and
response-access authority.

The source-only snapshot is authored with no adapter SOURCE_LOCK, artifacts,
access ledger, or output stream; a later sibling lock does not alter these
reviewed source bytes. Structural hex strings, caller-created dataclasses, deterministic
hash helpers, injected providers, and the explicitly nonauthoritative source
transition model grant no access. `calibrate`, `confirm`, and `heldout` refuse
before importing the producer. A separate Git-object-backed source-lock commit
and fresh Git-committed phase authorizations are required before any future
access. Verification supports a detached no-`.git` checkout only with an
explicit absolute trusted Git directory and always disables replace objects.
The source firewall freezes a closed, ordered AST import/name/call/attribute
inventory for every reviewed Python material. That inventory is defense in
depth rather than an independent trust root; the later external Git SOURCE_LOCK
is publication authority. Any package directory, including `__pycache__`, is
refused rather than silently joining the reviewed inventory.

## Claim ceiling

`PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE / MODEL_SPECIFIC_RELATIONS_ONLY`.
No universal, full-CWT, physical, empirical, or historically-unopened claim is
made.
