# G2 Deterministic-Model Validation Design

Status: approved in chat on 2026-08-20; implementation not started

## 1. Purpose And Gate Boundary

G2 builds and validates the deterministic foundation for the second thesis
problem: road-constrained air-ground heterogeneous cooperative pesticide
spraying with a mobile pesticide replenishment vehicle. It covers offline road
topology, physical-scale motion, discrete service events, pesticide accounting,
and deterministic replay.

G2 does not include policy networks, PPO, RL training, pilot comparison, formal
experiments, statistical claims, or sealed-test access. A passed G2 raises the
highest maturity only to M2: deterministic-model implementation verified.

The public algorithm remains SR-MAPPO. The resource is pesticide only. Battery
replenishment stays inactive. OSM data is a read-only simulation input and is
not evidence of field deployment.

## 2. Selected Implementation Approach

Build G2 from the accepted G1.1 baseline on the dedicated branch
`codex/problem2-g2-deterministic-validation`. The candidate branch
`origin/feature/problem2-code-framework` may inform module boundaries, but no
candidate implementation or claimed maturity is accepted by inheritance.
Every production behavior is implemented from the current contracts through a
fresh test-first cycle.

This approach was selected over bulk candidate-code transplantation, which
could retain its scale, provenance, and service-state defects, and over a fully
reference-free rewrite, which would repeat useful structural analysis without
improving the evidence boundary.

## 3. End-To-End Architecture

```text
read-only GraphML
-> source and CRS validation
-> EPSG:32643 metric projection
-> metric AOI clipping and line densification
-> six four-connected raster road graphs
-> topology validation and audited within-edge gap repair
-> deterministic NPZ plus JSON caches
-> metric UAV and vehicle movement
-> request and vehicle state machines
-> spray and transfer resource ledger
-> fixed-seed cross-process audit
```

The implementation is split into focused packages:

- `src/problem2/road/`: GraphML parsing, projection, rasterization, cache I/O,
  topology, and shortest paths.
- `src/problem2/dynamics/`: metric UAV and vehicle movement and action masks.
- `src/problem2/service/`: request lifecycle, vehicle lifecycle, deterministic
  selection, and service timing.
- `src/problem2/resources/`: spraying, transfers, and conservation ledger.
- `src/problem2/simulation/`: deterministic composition and event sequencing.
- `scripts/preprocess_g2_roads.py`: offline generation of six road caches.
- `scripts/audit_g2_deterministic.py`: one fail-closed G2 audit entry point.

`configs/problem2/g2_deterministic.yaml` is the single frozen G2 configuration.
`pyproject.toml` establishes the `src` package and declares Python 3.11 with
NumPy, PyYAML, NetworkX, Shapely, and PyProj. Torch and other RL dependencies
are outside the G2 dependency set. `requirements-g2.lock` records the exact
versions used to generate the accepted G2 evidence.

## 4. GIS Source, Projection, And AOI

The only G2 road source is the existing read-only file:

```text
D:/Pycharm/Locust_rl/data/jodhpur_drive.graphml
```

Its required SHA-256 is:

```text
B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462
```

The source coordinate system is WGS84 longitude/latitude (`EPSG:4326`).
Coordinates are transformed with `pyproj.Transformer(always_xy=True)` to the
local metric CRS `EPSG:32643` before any length, distance, clipping, or
rasterization operation.

The physical area of interest is centered at longitude `73.0351433`, latitude
`26.2967719`. Its projected axis-aligned bounds are exactly 500 m east-west by
300 m north-south around the projected center. The projected AOI is the
authoritative clipping boundary; a derived lon/lat bbox is metadata only.

Each GraphML edge uses its WKT `LINESTRING` geometry when present. An edge
without geometry uses the straight line between its endpoint coordinates. The
projected geometry is clipped against the AOI, so an edge crossing the AOI is
not lost merely because both original endpoints lie outside it. Non-finite,
malformed, or CRS-inconsistent coordinates fail preprocessing.

The source graph is directed traffic data, but the G2 road-access model is
explicitly undirected. Source edge direction and identifiers remain in
provenance mappings. This models physical road-constrained access rather than
traffic-rule routing and must not later be described as a traffic simulation.

No online download or fallback source is permitted.

## 5. Six-Scale Raster Topology

All six scales cover the same 500 m by 300 m physical AOI:

| Scale ID | Grid `(H, W)` | Frozen maximum steps |
|---|---:|---:|
| `g20x20_d2` | `(20, 20)` | 150 |
| `g20x30_d3` | `(20, 30)` | 180 |
| `g20x40_d3` | `(20, 40)` | 220 |
| `g30x30_d3` | `(30, 30)` | 220 |
| `g30x40_d4` | `(30, 40)` | 280 |
| `g30x50_d4` | `(30, 50)` | 350 |

These are resolution changes over one physical region, not evidence of larger
physical operating areas. Cell width is `500 / W` metres and cell height is
`300 / H` metres. Row zero is north and column zero is west. Boundary points
are clamped only at the AOI maximum edge; other mapping uses half-open cells.

Projected road lines are densified to a maximum segment length of 5 m, then
rasterized with a deterministic supercover algorithm. The output graph is
strictly four-connected. If ordered cells from one source edge remain only
diagonally adjacent, the bridge candidate whose center has the smaller
perpendicular distance to that same source segment is inserted; an exact tie
uses lexicographic `(row, column)` order. Each insertion records endpoints,
metric bridge length, source edge ID, source segment, and reason.

Gap repair is allowed only inside one demonstrably continuous source edge.
There is no nearest-component repair, no connection between different source
edges, and no geometric rescaling or translation to fill the grid.

All connected components are retained and labelled in the cache. Runtime
vehicle placement and routing use only the largest component. Component-size
ties are resolved by the lexicographically smallest member cell. Mappings from
original source node IDs and edge IDs to raster cells are retained in metadata.

The five vehicle action indices are frozen as:

```text
0 stay, 1 up, 2 down, 3 left, 4 right
```

Only graph edges create directional legality. `stay` is always legal for a
road node unless a later gate introduces a separately tested terminal state.

## 6. Road Cache Contract

Each scale writes:

```text
outputs/problem2_sr_mappo_v1/g2/roads/<scale_id>/road_graph.npz
outputs/problem2_sr_mappo_v1/g2/roads/<scale_id>/metadata.json
```

The NPZ contains at least:

- `road_mask[H,W]`;
- `action_mask[H,W,5]`;
- `component_id[H,W]`;
- canonical node rows and columns;
- canonical undirected edge endpoints and metric weights;
- per-edge source-mapping indices.

Metadata contains at least:

- source absolute path and SHA-256;
- source and target CRS;
- source and projected bboxes;
- projected AOI and physical extent;
- grid shape and cell dimensions;
- densification and gap-repair policies;
- original-node and original-edge mappings;
- component sizes and primary-component identity;
- complete repair log;
- adjacency and canonical-array content checksums;
- cache schema and preprocessing versions;
- generator file SHA-256 and generator Git commit.

The generator Git commit is the newest commit that changes the G2 package,
configuration, dependency declarations, or G2 CLI scripts. Evidence-only and
documentation-only commits do not change this provenance value.

Cache loading recomputes and validates checksums and dimensions. A mismatch in
source hash, CRS, AOI, grid shape, preprocessing version, generator hash, or
content checksum is a hard cache miss and is rejected. A cache generated by a
dirty or uncommitted generator is not phase evidence.

Outputs are written to temporary files in the destination directory, flushed,
then atomically replaced. A failed run does not replace the last complete
cache. Canonical sorting and canonical JSON serialization make semantic
content independent of Python hash iteration.

## 7. Metric Movement Contract

The frozen physical values inherited from G1.1 are:

- `dt = 1.0 s`;
- UAV speed `5.0 m/s`;
- vehicle speed `8.0 m/s`.

UAV position is stored as continuous projected metres. The raster cell is a
derived observation and spatial-index value. A legal directional UAV action
moves at most `speed * dt` metres and clips at the physical AOI boundary.
`stay` and `spray` do not move.

Vehicle position is an interpolation along a raster road edge. State includes
the last reached node, current target node, direction, edge progress, and metric
position. At a road node a legal direction selects the adjacent road edge.
During an incomplete traversal, the next action mask permits only continuation
in the selected direction; the environment never overrides a sampled action.

Each active vehicle movement step supplies at most `speed * dt` metres. If the
vehicle reaches a node and the same cardinal direction has a unique successor,
it may continue along that successor with the unused distance from the current
step. It stops at a branch, dead end, direction change, or exhausted step
distance. Unfinished edge progress carries across steps; unused distance at a
decision-required stop does not carry across time. `stay`, waiting, and service
do not accumulate travel credit.

The service distance is the Euclidean metric distance between current UAV and
vehicle positions. Service may start only while the vehicle is stopped at a
road node and the distance is at most 15 m.

Passing an action that was false in the stored mask raises an illegal-action
error before state mutation. It is never silently converted to `stay`.
Movement events record intended action, legal mask, available distance,
actual distance, edge progress, route distance, boundary clipping, and final
position.

## 8. Request And Vehicle State Machines

Each UAV has at most one active request. Request states are:

```text
pending -> reserved -> serving -> completed
                         \-> cancelled
```

Cancellation is permitted only by an explicit terminal or invalid-request
rule and must include a reason. Vehicle modes are:

```text
idle <-> transit
idle -> serving -> idle
```

Inventory depletion is a separate boolean flag, not a vehicle mode. One
vehicle serves at most one UAV, and one UAV is reserved by at most one vehicle.

The operational UAV pesticide capacity is the nominal 1.2 L multiplied by the
0.9 usable fraction, or 1.08 L. With nonzero spray flow, a request is created
when:

```text
remaining_pesticide_L / spray_flow_L_per_s
<= estimated_time_to_service_s + 10 s
```

Zero spray flow does not trigger this endurance rule. Requested volume is the
positive gap to 1.08 L, bounded by the per-service cap. The service-delay
estimate uses current metric shortest-road travel time to a reachable
rendezvous node, queued locked-service time, setup time, and transfer time. An
unreachable estimate is infinity and may trigger a pending request, but it does
not make that request serviceable.

A request is currently serviceable only when it is pending, unreserved, its
UAV is within 15 m, the vehicle is idle at a road node, and vehicle inventory
is positive. Selection is FIFO by creation step among currently serviceable
requests, with UAV ID as the same-step tie-breaker. An old remote or unreachable
request never blocks a nearby serviceable request.

Reservation and service start may occur in the same simulation step but emit
separate state-transition events. Both UAV and vehicle are then service-locked,
and their stored action masks permit only `stay` until completion.

Planned and actual transfer volume is:

```text
min(UAV usable-capacity gap, 1.08 L service cap,
    vehicle remaining inventory)
```

Service duration is:

```text
ceil((10 s setup + transfer_volume / (4 L/min)) / 1 s)
```

The start step is service step one. No gradual transfer occurs. On the final
service boundary the full actual transfer is applied atomically, then request
and vehicle states transition to completed and idle. Service locks make the
capacity gap stable; the completion boundary nevertheless recomputes and
validates the legal minimum before committing.

If an episode ends exactly on the final service step, transfer and completion
occur before termination. A service that has not reached its completion
boundary at terminal time is cancelled and transfers nothing.

## 9. Pesticide Conservation Contract

The G1.1 spray flow is 1.2 L/min, so one full one-second spray action consumes
0.02 L. If less is available, the action consumes only the actual remaining
amount and records the partial application. A transfer is internal movement of
pesticide and never changes system total.

Every spray and transfer event records before values, delta, and after values.
The ledger validates after each event, each step, and the episode:

```text
initial UAV pesticide total + initial vehicle inventory
- cumulative actual sprayed amount
= current UAV pesticide total + current vehicle inventory
```

The absolute tolerance is `1e-9 L`. All values must be finite. Negative
resource, UAV resource above 1.08 L, duplicate transfer, or conservation error
rejects the transaction before externally visible state is committed.

## 10. Frozen G2 Step Order

The deterministic integration fixture uses this order:

1. Build observations and action masks from state `t`.
2. Accept already-sampled UAV and vehicle actions plus their stored masks.
3. Validate actions and apply legal movement or spray debit.
4. Generate threshold-based requests from post-action pesticide state.
5. Reserve one eligible request with deterministic FIFO selection.
6. Start or advance locked service.
7. Transfer pesticide on the declared completion boundary.
8. Advance no-op G2 environment hooks reserved for later pest and wind logic.
9. Evaluate maximum-horizon termination; no reward claim is made in G2.
10. Commit an event-complete log and conservation snapshot.

This order is transactional. A validation failure leaves the pre-step state
unchanged. G3 must use the same stored masks for behavior sampling and PPO
replay, but PPO behavior is outside this specification.

## 11. Determinism And Audit Artifacts

All stochastic fixtures use an explicitly passed
`numpy.random.Generator(PCG64(seed))`; no module-global random generator is
allowed. The integrated G2 audit uses training seed 42 only. It does not read
validation or sealed-test seeds.

Nodes, edges, requests, events, and JSON keys have canonical stable ordering.
Two subprocesses run the same fixture under different `PYTHONHASHSEED` values.
Their topology content checksums and canonical event JSONL must be byte
identical.

The audit writes only below:

```text
outputs/problem2_sr_mappo_v1/g2/
```

Required phase evidence is:

- six road cache pairs;
- `g2-deterministic-audit.json`;
- `deterministic-event-trace.jsonl`;
- a manifest containing artifact hashes and the generator commit.

## 12. Failure Policy

The preprocessing and audit CLIs return nonzero and do not publish partial
outputs for any of the following:

- missing or hash-mismatched source;
- invalid CRS, projection, AOI, geometry, or non-finite number;
- stale or corrupt cache metadata or arrays;
- non-four-connected runtime edge;
- unlogged or cross-source gap repair;
- illegal action or mask inconsistency;
- illegal request or vehicle transition;
- duplicate reservation or simultaneous service;
- negative, over-capacity, or non-conserved pesticide;
- nondeterministic cross-process output;
- attempted validation/sealed-seed or external-output access.

Errors contain the scale, step or entity identifier, violated invariant, and
expected versus observed values where applicable.

## 13. Required Verification

Road and cache tests must cover:

- projection and known-point metric-distance sanity;
- AOI clipping, WKT and endpoint fallback geometry;
- line densification, four-connectivity, and logged within-edge repairs;
- source-node and source-edge mappings;
- all six cache shapes and metadata fields;
- invalidation for source, CRS, AOI, shape, version, generator, and content;
- A* and independent Dijkstra distance agreement within `1e-9 m` on sampled
  primary-component pairs.

Motion and mask tests must cover:

- equal metric speed limits across all six scales;
- incomplete edge progress, same-direction continuation, branches, dead ends,
  boundary clipping, stay, and service lock;
- zero probability for illegal masked actions and zero successful illegal
  executions;
- fail-closed direct illegal-action calls without state mutation.

Service and resource tests must cover:

- threshold request generation and the zero-flow rule;
- simultaneous requests with FIFO and UAV-ID tie-breaking;
- an older unreachable request with a newer serviceable request;
- multiple UAV arrivals while the vehicle is busy;
- partial refill, exact vehicle depletion, and no negative resource;
- transaction rollback on an invariant violation;
- episode termination on and before the final service step;
- event, step, and episode conservation within `1e-9 L`.

Integration tests must cover the frozen event order, exact event completeness,
fixed-seed event replay, and cross-process hash-seed reproducibility.

G2 passes only when all of the following fresh commands succeed:

```powershell
python -m pytest tests/g2 -q
python -m pytest -q
python scripts/preprocess_g2_roads.py --config configs/problem2/g2_deterministic.yaml
python scripts/audit_g2_deterministic.py --config configs/problem2/g2_deterministic.yaml --report outputs/problem2_sr_mappo_v1/g2/g2-deterministic-audit.json
git diff --check
```

## 14. Persistence And Permitted Claims

Implementation, tests, configuration, caches, audit reports, and manifests are
committed on the dedicated G2 branch. The branch is pushed without rewriting
history. `docs/PROJECT_STATE.md` then records the pushed content commit, exact
verification commands and results, remaining evidence limits, and the final
persistence-record commit.

After these conditions pass, the permitted statement is:

> The G2 deterministic road, physical-motion, service-state, and pesticide-
> conservation implementation passed its registered verification suite.

The implementation must not claim that mobile support improves treatment,
that SR-MAPPO outperforms a comparison, that formal experiments exist, or that
the OSM-driven simulation is a real deployment. RL work begins only at G3;
training cannot begin until G3 passes, formal experiments cannot begin until
G5 is frozen and G6 is authorized, and sealed tests remain locked until G7.

## 15. Fix-Round Correction Record

The first implementation review found that several requirements were represented
only as events or per-file behavior, which was insufficient for an auditable
deterministic gate. The accepted implementation correction is:

- Production CLIs accept only the frozen output root. The former test flag and
  environment-variable bypass were removed; temporary-output tests use an
  in-process test API and cannot alter CLI behavior.
- Reservation is a real `PENDING -> RESERVED` replacement state before the
  `RESERVED -> SERVING` replacement. The two transitions remain separate events
  even when they occur in one step.
- Vehicle road-state validation checks node range, primary-component membership,
  node coordinates, transit edge progress, target, direction, and interpolated
  position before masks, routing, selection, or service.
- Motion events now carry the legal mask, available and actual distance, edge
  progress, cumulative route distance, boundary clipping, and final position.
- Six caches are staged and reload-validated under a temporary `roads`
  directory, then published by one directory swap with backup recovery. A
  failed generation preserves the previous complete set.
- Cache expectations bind source CRS and generator commit in addition to the
  existing source hash, target CRS, AOI, grid, preprocessing version, and tree
  hash.
- Config, inventory-depletion, and non-finite ledger validation are fail-closed
  at their public boundaries.

These corrections strengthen implementation semantics without changing the
scientific question, frozen physical values, seed boundary, or maturity claim.
