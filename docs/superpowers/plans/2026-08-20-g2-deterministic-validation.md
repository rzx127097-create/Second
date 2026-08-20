# G2 Deterministic-Model Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and persist the verified deterministic road, metric-motion, service-state, pesticide-conservation, and replay foundation required to pass Problem 2 gate G2.

**Architecture:** Parse and project the read-only Jodhpur GraphML once, create six deterministic four-connected road caches, and expose small functional modules over immutable shared domain states. Compose motion, requests, atomic service, and resource accounting in a transactional step engine, then verify it through unit, integration, CLI, and cross-process reproducibility tests.

**Tech Stack:** Python 3.11, NumPy, PyYAML, NetworkX, Shapely, PyProj, pytest, standard-library JSON/hashlib/subprocess/pathlib/dataclasses.

**Spec:** `docs/superpowers/specs/2026-08-20-g2-deterministic-validation-design.md`

## Global Constraints

- Work only on `codex/problem2-g2-deterministic-validation` and persist every important G2 artifact to this repository and `origin`.
- Keep the public algorithm identity `SR-MAPPO`; do not add HAPPO or another public method name.
- Pesticide is the only replenished resource; battery replenishment remains inactive.
- Treat `D:/Pycharm/Locust_rl/data/jodhpur_drive.graphml` as read-only and require SHA-256 `B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462`.
- Use `EPSG:4326 -> EPSG:32643`, a 500 m by 300 m AOI centered at `(73.0351433, 26.2967719)`, and the six frozen grid shapes.
- Write generated evidence only under `outputs/problem2_sr_mappo_v1/g2/`.
- Use only training seed 42 for the integrated deterministic audit; do not access validation or sealed-test seeds.
- Use TDD for every production behavior: observe the intended failure before adding its implementation.
- Fail closed on invalid provenance, topology, masks, state transitions, non-finite values, and resource accounting.
- G2 completion permits only an M2 deterministic-implementation claim; do not train RL or make comparative outcome claims.

---

### Task 1: Package, Frozen Configuration, And Shared Domain Types

**Files:**
- Create: `pyproject.toml`
- Create: `requirements-g2.lock`
- Create: `configs/problem2/g2_deterministic.yaml`
- Create: `src/problem2/__init__.py`
- Create: `src/problem2/config.py`
- Create: `src/problem2/domain.py`
- Create: `tests/g2/__init__.py`
- Create: `tests/g2/test_config_and_domain.py`

**Interfaces:**
- Produces: `ScaleConfig`, `G2Config`, `load_g2_config(path: Path) -> G2Config`.
- Produces: `Action`, `RequestStatus`, `VehicleMode`, `UavState`, `VehicleState`, `ServiceRequest`, `EpisodeState`, and `Event` immutable dataclasses/enums.
- Consumes: the G1.1 values in `docs/evidence/g1/parameter_registry.yaml` and scale/horizon values in `docs/evidence/g1/experiment_matrix.yaml`.

- [x] **Step 1: Write failing configuration and state-invariant tests**

```python
def test_loads_frozen_six_scale_metric_contract():
    config = load_g2_config(CONFIG_PATH)
    assert config.target_crs == "EPSG:32643"
    assert config.extent_m == (500.0, 300.0)
    assert [(s.scale_id, s.grid_shape, s.max_steps) for s in config.scales] == [
        ("g20x20_d2", (20, 20), 150),
        ("g20x30_d3", (20, 30), 180),
        ("g20x40_d3", (20, 40), 220),
        ("g30x30_d3", (30, 30), 220),
        ("g30x40_d4", (30, 40), 280),
        ("g30x50_d4", (30, 50), 350),
    ]

def test_rejects_nonfinite_and_non_pesticide_configuration(tmp_path):
    payload = valid_config_payload()
    payload["physics"]["vehicle_speed_mps"] = float("nan")
    assert_load_error(payload, "finite")
    payload = valid_config_payload()
    payload["resources"]["battery_replenishment_enabled"] = True
    assert_load_error(payload, "battery replenishment")
```

- [x] **Step 2: Run the tests and verify the intended import failure**

Run: `python -m pytest tests/g2/test_config_and_domain.py -q`

Expected: collection fails because `problem2.config` and `problem2.domain` do not exist.

- [x] **Step 3: Add minimal packaging, exact YAML values, strict parsing, and immutable domain types**

```python
@dataclass(frozen=True)
class G2Config:
    source_path: Path
    source_sha256: str
    source_crs: str
    target_crs: str
    center_lonlat: tuple[float, float]
    extent_m: tuple[float, float]
    scales: tuple[ScaleConfig, ...]
    dt_s: float
    uav_speed_mps: float
    vehicle_speed_mps: float
    usable_capacity_l: float
    spray_flow_lpm: float
    vehicle_inventory_l: float
    transfer_rate_lpm: float
    setup_time_s: float
    service_cap_l: float
    request_margin_s: float
    rendezvous_radius_m: float
    tolerance: float
```

Validate required keys, exact six scale IDs, finite positive physical values,
the pesticide-only flag, source path, and allowed output root. Define states as
frozen dataclasses so failed transactional steps cannot leak partial mutation.

- [x] **Step 4: Run focused and baseline tests**

Run: `python -m pytest tests/g2/test_config_and_domain.py -q`

Expected: all Task 1 tests pass.

Run: `python -m pytest -q`

Expected: all existing G0/G1 tests and Task 1 tests pass.

- [x] **Step 5: Commit Task 1**

```powershell
git add pyproject.toml requirements-g2.lock configs/problem2/g2_deterministic.yaml src/problem2 tests/g2
git commit -m "feat: freeze g2 deterministic configuration"
```

### Task 2: Verified GraphML Projection And AOI Clipping

**Files:**
- Create: `src/problem2/road/__init__.py`
- Create: `src/problem2/road/models.py`
- Create: `src/problem2/road/source.py`
- Create: `tests/g2/test_road_source.py`
- Create: `tests/g2/fixtures/tiny_road.graphml`

**Interfaces:**
- Consumes: `G2Config` from Task 1.
- Produces: `ProjectedRoadSource`, `ProjectedRoadNode`, and `ProjectedRoadEdge`.
- Produces: `load_projected_road_source(config: G2Config) -> ProjectedRoadSource`.
- `ProjectedRoadSource` carries source hash, CRS values, lon/lat bbox, projected AOI, projected nodes, and clipped projected edge coordinate sequences.

- [x] **Step 1: Write failing source-integrity and projection tests**

```python
def test_projects_known_lonlat_offset_to_metric_distance(tiny_config):
    source = load_projected_road_source(tiny_config)
    distance = source.nodes["east"].distance_to(source.nodes["center"])
    assert distance == pytest.approx(100.0, abs=0.25)

def test_keeps_edge_that_crosses_aoi_with_endpoints_outside(tiny_config):
    source = load_projected_road_source(tiny_config)
    crossing = next(edge for edge in source.edges if edge.source_id == "cross")
    assert crossing.coords_m[0][0] == pytest.approx(source.aoi_bounds_m[0])
    assert crossing.coords_m[-1][0] == pytest.approx(source.aoi_bounds_m[2])

def test_rejects_source_hash_mismatch(tiny_config):
    with pytest.raises(SourceIntegrityError, match="SHA-256"):
        load_projected_road_source(replace(tiny_config, source_sha256="0" * 64))
```

Include cases for WKT geometry, endpoint fallback, malformed geometry,
non-finite node coordinates, and source CRS mismatch.

- [x] **Step 2: Run tests and verify the missing-module failure**

Run: `python -m pytest tests/g2/test_road_source.py -q`

Expected: collection fails because `problem2.road.source` does not exist.

- [x] **Step 3: Implement hash verification, GraphML loading, projection, and clipping**

```python
def load_projected_road_source(config: G2Config) -> ProjectedRoadSource:
    actual_hash = sha256_file(config.source_path)
    if actual_hash.upper() != config.source_sha256.upper():
        raise SourceIntegrityError(...)
    graph = nx.read_graphml(config.source_path)
    transformer = Transformer.from_crs(
        config.source_crs, config.target_crs, always_xy=True
    )
    center_x, center_y = transformer.transform(*config.center_lonlat)
    aoi = box(center_x - 250.0, center_y - 150.0,
              center_x + 250.0, center_y + 150.0)
    ...
```

Use `shapely.wkt.loads`, `shapely.ops.transform`, and intersection with the
projected AOI. Canonicalize IDs as strings and sort edges by source ID plus
endpoint IDs.

- [x] **Step 4: Verify Task 2 and full regression**

Run: `python -m pytest tests/g2/test_road_source.py -q`

Expected: all projection/source tests pass.

Run: `python -m pytest -q`

Expected: the full suite passes.

- [x] **Step 5: Commit Task 2**

```powershell
git add src/problem2/road tests/g2/test_road_source.py tests/g2/fixtures/tiny_road.graphml
git commit -m "feat: project and clip offline g2 roads"
```

### Task 3: Four-Connected Rasterization And Audited Caches

**Files:**
- Create: `src/problem2/road/raster.py`
- Create: `src/problem2/road/cache.py`
- Create: `tests/g2/test_road_raster.py`
- Create: `tests/g2/test_road_cache.py`

**Interfaces:**
- Consumes: `ProjectedRoadSource` and `ScaleConfig`.
- Produces: `RasterRoadGraph`, `RepairRecord`, and `RoadCacheExpectation`.
- Produces: `rasterize_road_source(source, scale, max_segment_m=5.0) -> RasterRoadGraph`.
- Produces: `write_road_cache(graph, source, config, root, generator_commit) -> tuple[Path, Path]`.
- Produces: `load_road_cache(npz_path, metadata_path, expected) -> RasterRoadGraph`.

- [x] **Step 1: Write failing raster behavior tests**

```python
def test_diagonal_source_segment_becomes_logged_four_connected_path():
    graph = rasterize_road_source(diagonal_source(), SCALE_20, max_segment_m=5.0)
    for u, v in graph.edges:
        dr = abs(int(graph.node_rows[u]) - int(graph.node_rows[v]))
        dc = abs(int(graph.node_cols[u]) - int(graph.node_cols[v]))
        assert dr + dc == 1
    assert graph.repairs
    assert {repair.reason for repair in graph.repairs} == {"same_source_edge_diagonal_bridge"}

def test_nearby_independent_components_are_not_repaired():
    graph = rasterize_road_source(two_close_components(), SCALE_20)
    assert sorted(graph.component_sizes, reverse=True) == [2, 1]
    assert not any(r.source_edge_id == "cross-component" for r in graph.repairs)
```

Also assert the exact five-action order, primary-component tie-break, source
node/edge mappings, all six output shapes, and anisotropic metric edge lengths.

- [x] **Step 2: Run raster tests and verify expected missing symbols**

Run: `python -m pytest tests/g2/test_road_raster.py -q`

Expected: collection fails because the raster interfaces do not exist.

- [x] **Step 3: Implement deterministic densification, supercover mapping, four-connected adjacency, and components**

```python
def _bridge_cell(a, b, segment, cell_center):
    candidates = ((b[0], a[1]), (a[0], b[1]))
    return min(
        candidates,
        key=lambda cell: (segment.distance(Point(cell_center(cell))), cell),
    )
```

Deduplicate ordered cells without losing path order. Build canonical nodes and
undirected edges, calculate cell-center metric edge weights, label every
component, and choose the primary component deterministically.

- [x] **Step 4: Write failing cache integrity and invalidation tests**

```python
@pytest.mark.parametrize("field", ["source_sha256", "target_crs", "aoi_bounds_m",
                                   "grid_shape", "preprocess_version",
                                   "generator_sha256"])
def test_cache_rejects_changed_expectation(cache_pair, field):
    expected = mutate_expectation(valid_expectation(cache_pair), field)
    with pytest.raises(CacheValidationError, match=field):
        load_road_cache(*cache_pair, expected)

def test_cache_rejects_array_tampering(cache_pair):
    rewrite_first_edge_weight(cache_pair[0], 999.0)
    with pytest.raises(CacheValidationError, match="content checksum"):
        load_road_cache(*cache_pair, valid_expectation(cache_pair))
```

- [x] **Step 5: Run cache tests and verify the expected missing-interface failure**

Run: `python -m pytest tests/g2/test_road_cache.py -q`

Expected: tests fail because cache I/O is not implemented.

- [x] **Step 6: Implement canonical content hashing and atomic NPZ/JSON cache I/O**

Hash every array using name, dtype, shape, and C-order bytes. Store sorted JSON
with UTF-8 and `allow_nan=False`. Write sibling temporary files, validate them,
then replace final paths. Record dependency versions, generator file hash, and
generator commit in metadata.

- [x] **Step 7: Run Task 3 and full tests**

Run: `python -m pytest tests/g2/test_road_raster.py tests/g2/test_road_cache.py -q`

Expected: all Task 3 tests pass.

Run: `python -m pytest -q`

Expected: the full suite passes.

- [x] **Step 8: Commit Task 3**

```powershell
git add src/problem2/road tests/g2/test_road_raster.py tests/g2/test_road_cache.py
git commit -m "feat: build audited four-connected road caches"
```

### Task 4: Metric Shortest Paths And Scale-Safe Motion

**Files:**
- Create: `src/problem2/road/search.py`
- Create: `src/problem2/dynamics/__init__.py`
- Create: `src/problem2/dynamics/motion.py`
- Create: `tests/g2/test_shortest_path.py`
- Create: `tests/g2/test_motion.py`

**Interfaces:**
- Consumes: `RasterRoadGraph`, `Action`, `UavState`, and `VehicleState`.
- Produces: `astar_distance(graph, start, goal) -> float` and `dijkstra_distance(graph, start, goal) -> float`.
- Produces: `uav_action_mask`, `move_uav`, `vehicle_action_mask`, and `move_vehicle`.
- Every move returns a new immutable state and an `Event`; invalid input raises before returning either.

- [x] **Step 1: Write failing hand-derived shortest-path tests**

```python
def test_astar_uses_anisotropic_metric_weights(hand_graph):
    assert astar_distance(hand_graph, 0, 3) == pytest.approx(35.0)

def test_astar_matches_independent_dijkstra_on_sampled_pairs(real_cache):
    for start, goal in fixed_seed_pairs(real_cache.primary_nodes, seed=42, count=20):
        assert astar_distance(real_cache, start, goal) == pytest.approx(
            dijkstra_distance(real_cache, start, goal), abs=1e-9
        )
```

- [x] **Step 2: Run shortest-path tests and observe the intended failure**

Run: `python -m pytest tests/g2/test_shortest_path.py -q`

Expected: collection fails because `problem2.road.search` does not exist.

- [x] **Step 3: Implement A* and an independent NetworkX Dijkstra oracle**

Use a heap-based A* with anisotropic Manhattan lower bound and stable node-ID
tie-breaking. Build the NetworkX oracle directly from canonical cached edges;
do not call A* helpers from the oracle.

- [x] **Step 4: Write failing UAV/vehicle motion and mask tests**

```python
@pytest.mark.parametrize("scale_id", ALL_SCALE_IDS)
def test_uav_metric_displacement_is_scale_independent(scale_id, config):
    state = UavState("u0", x_m=250.0, y_m=150.0, pesticide_l=1.08)
    moved, event = move_uav(state, Action.RIGHT, config, grid_shape(scale_id))
    assert moved.x_m - state.x_m == pytest.approx(5.0)
    assert event.distance_m == pytest.approx(5.0)

def test_vehicle_carries_only_unfinished_edge_progress(hand_graph):
    first, _ = move_vehicle(vehicle_at_node(0), Action.RIGHT, hand_graph, 8.0)
    assert first.edge_progress_m == pytest.approx(8.0)
    second, _ = move_vehicle(first, Action.RIGHT, hand_graph, 8.0)
    assert second.edge_progress_m == pytest.approx(16.0)

def test_illegal_action_raises_without_state_change(hand_graph):
    state = vehicle_at_node(0)
    with pytest.raises(IllegalActionError):
        move_vehicle(state, Action.UP, hand_graph, 8.0)
    assert state == vehicle_at_node(0)
```

Cover same-direction multi-edge continuation, branch stop, dead end, stay,
boundary clipping, transit masks, service locks, and zero illegal-action
probability after masked categorical normalization.

- [x] **Step 5: Run motion tests and observe the intended missing-symbol failures**

Run: `python -m pytest tests/g2/test_motion.py -q`

Expected: collection fails because movement functions do not exist.

- [x] **Step 6: Implement pure metric movement functions and fail-closed masks**

UAV movement uses projected continuous coordinates. Vehicle movement consumes
at most `vehicle_speed_mps * dt_s`, interpolates on canonical road edges, and
uses the stored direction while transit. It drops unused within-step distance
at decision-required stops and never accrues distance during stay/service.

- [x] **Step 7: Run Task 4 and full tests**

Run: `python -m pytest tests/g2/test_shortest_path.py tests/g2/test_motion.py -q`

Expected: all Task 4 tests pass.

Run: `python -m pytest -q`

Expected: the full suite passes.

- [x] **Step 8: Commit Task 4**

```powershell
git add src/problem2/road/search.py src/problem2/dynamics tests/g2/test_shortest_path.py tests/g2/test_motion.py
git commit -m "feat: add metric paths and physical motion"
```

### Task 5: Request Lifecycle, Atomic Service, And Resource Ledger

**Files:**
- Create: `src/problem2/resources/__init__.py`
- Create: `src/problem2/resources/ledger.py`
- Create: `src/problem2/service/__init__.py`
- Create: `src/problem2/service/state_machine.py`
- Create: `tests/g2/test_resource_ledger.py`
- Create: `tests/g2/test_service_state_machine.py`

**Interfaces:**
- Consumes: shared domain states, `G2Config`, and current metric positions.
- Produces: `new_ledger`, `apply_spray`, `apply_transfer`, and `assert_conserved`.
- Produces: `should_request`, `create_request`, `select_serviceable_request`, `start_service`, `advance_service`, and `cancel_terminal_requests`.
- Every operation returns replacement immutable states plus canonical events.

- [x] **Step 1: Write failing event/step/episode conservation tests**

```python
def test_partial_spray_and_transfer_preserve_total():
    ledger = new_ledger([uav("u0", 0.01)], vehicle_inventory_l=0.5)
    sprayed_uav, ledger, spray = apply_spray(uav("u0", 0.01), ledger, 0.02)
    assert spray.delta_l == pytest.approx(0.01)
    filled_uav, inventory, ledger, transfer = apply_transfer(
        sprayed_uav, 0.5, ledger, service_cap_l=1.08, usable_capacity_l=1.08
    )
    assert transfer.delta_l == pytest.approx(0.5)
    assert_conserved([filled_uav], inventory, ledger, tolerance=1e-9)

def test_invalid_transfer_rolls_back_inputs():
    before = uav("u0", 1.08)
    with pytest.raises(ResourceInvariantError):
        apply_transfer(before, -0.1, new_ledger([before], -0.1), 1.08, 1.08)
    assert before.pesticide_l == 1.08
```

- [x] **Step 2: Run resource tests and observe the intended import failure**

Run: `python -m pytest tests/g2/test_resource_ledger.py -q`

Expected: collection fails because `problem2.resources.ledger` does not exist.

- [x] **Step 3: Implement finite immutable resource transactions**

Compute spray as `min(available, 0.02 L)` and transfer as the minimum of usable
capacity gap, service cap, and vehicle inventory. Reject negative or non-finite
inputs before constructing replacement objects. Track cumulative sprayed and
transferred volumes and check the hand-derived conservation equation.

- [x] **Step 4: Write failing request and service-transition tests**

```python
def test_same_step_fifo_tie_breaks_by_uav_id():
    requests = [pending("u2", step=4), pending("u1", step=4)]
    chosen = select_serviceable_request(requests, idle_vehicle(), uavs_nearby())
    assert chosen.uav_id == "u1"

def test_old_unreachable_request_does_not_block_new_serviceable_request():
    requests = [pending("u0", step=1), pending("u1", step=2)]
    chosen = select_serviceable_request(
        requests, idle_vehicle(), {"u0": far_uav(), "u1": near_uav()}
    )
    assert chosen.uav_id == "u1"

def test_transfer_occurs_only_on_completion_boundary():
    state = start_fixture(planned_transfer_l=1.0, duration_steps=25)
    for _ in range(24):
        state, events = advance_service(state, CONFIG)
        assert not any(event.kind == "transfer" for event in events)
    state, events = advance_service(state, CONFIG)
    assert [event.kind for event in events][-2:] == ["transfer", "service_completed"]
```

Also cover request threshold equality, zero spray flow, one active request per
UAV, multiple arrivals while busy, partial refill, exact vehicle depletion,
duplicate reservation rejection, and terminal cancellation before/on the
completion step.

- [x] **Step 5: Run service tests and observe the intended missing-interface failure**

Run: `python -m pytest tests/g2/test_service_state_machine.py -q`

Expected: collection fails because the service state machine does not exist.

- [x] **Step 6: Implement deterministic request selection and atomic service transitions**

Use `(created_step, uav_id, request_id)` as the stable selection key after
filtering to currently serviceable requests. Emit separate reserved and serving
events even when both transitions happen in one step. Lock both participants,
advance one service step on the start step, and transfer atomically only when
the counter reaches the frozen completion boundary.

- [x] **Step 7: Run Task 5 and full tests**

Run: `python -m pytest tests/g2/test_resource_ledger.py tests/g2/test_service_state_machine.py -q`

Expected: all Task 5 tests pass.

Run: `python -m pytest -q`

Expected: the full suite passes.

- [x] **Step 8: Commit Task 5**

```powershell
git add src/problem2/resources src/problem2/service tests/g2/test_resource_ledger.py tests/g2/test_service_state_machine.py
git commit -m "feat: enforce g2 service and pesticide conservation"
```

### Task 6: Transactional Step Engine And Cross-Process Replay

**Files:**
- Create: `src/problem2/simulation/__init__.py`
- Create: `src/problem2/simulation/engine.py`
- Create: `src/problem2/simulation/replay.py`
- Create: `tests/g2/test_simulation_engine.py`
- Create: `tests/g2/test_reproducibility.py`

**Interfaces:**
- Consumes: road graph, config, immutable episode state, UAV actions, vehicle action, and stored masks.
- Produces: `step_episode(state, actions, stored_masks, graph, config) -> EpisodeState`.
- Produces: `run_deterministic_fixture(graph, config, seed=42) -> tuple[EpisodeState, tuple[Event, ...]]`.
- Produces: `canonical_event_jsonl(events) -> bytes` and `replay_digest(events) -> str`.

- [x] **Step 1: Write failing exact-order and rollback integration tests**

```python
def test_step_emits_events_in_frozen_order(integration_fixture):
    next_state = step_episode(**integration_fixture)
    assert [event.phase for event in next_state.last_step_events] == [
        "action", "spray", "request", "reserve", "service", "conservation", "termination"
    ]

def test_failed_step_returns_no_partial_state(integration_fixture):
    before = integration_fixture["state"]
    bad_masks = replace_vehicle_mask(integration_fixture["stored_masks"], all_false=True)
    with pytest.raises(StepTransactionError):
        step_episode(**{**integration_fixture, "stored_masks": bad_masks})
    assert integration_fixture["state"] == before
```

Include termination exactly at and one step before the service-completion
boundary, and validate conservation after every produced step.

- [x] **Step 2: Run engine tests and observe the intended missing-module failure**

Run: `python -m pytest tests/g2/test_simulation_engine.py -q`

Expected: collection fails because `problem2.simulation.engine` does not exist.

- [x] **Step 3: Implement the pure transactional step composition**

Build masks from state `t`, require equality with supplied stored masks, apply
movement/spray, create requests, reserve, advance service, run the no-op G2
environment hook, terminate, then validate and return the replacement state.
Wrap invariant errors with scale/step/entity context without mutating inputs.

- [x] **Step 4: Write failing canonical replay and subprocess tests**

```python
def test_event_json_is_canonical():
    assert canonical_event_jsonl(reversed_key_events()) == EXPECTED_EVENT_BYTES

def test_hash_seed_does_not_change_fixture(tmp_path):
    first = run_worker(tmp_path / "a.jsonl", python_hash_seed="1")
    second = run_worker(tmp_path / "b.jsonl", python_hash_seed="98765")
    assert first.read_bytes() == second.read_bytes()
```

- [x] **Step 5: Run replay tests and verify the intended missing-interface failure**

Run: `python -m pytest tests/g2/test_reproducibility.py -q`

Expected: tests fail because replay helpers are not implemented.

- [x] **Step 6: Implement PCG64-only fixture generation and canonical JSONL**

Require an explicit `Generator(PCG64(seed))`, sort every collection crossing a
serialization boundary, format events through `json.dumps(sort_keys=True,
separators=(",", ":"), allow_nan=False)`, and expose a subprocess worker entry
that receives paths and seed as explicit arguments.

- [x] **Step 7: Run Task 6 and full tests**

Run: `python -m pytest tests/g2/test_simulation_engine.py tests/g2/test_reproducibility.py -q`

Expected: all Task 6 tests pass.

Run: `python -m pytest -q`

Expected: the full suite passes.

- [x] **Step 8: Commit Task 6**

```powershell
git add src/problem2/simulation tests/g2/test_simulation_engine.py tests/g2/test_reproducibility.py
git commit -m "feat: add deterministic g2 transition replay"
```

### Task 7: Fail-Closed Preprocessor, Unified Audit, And Real Caches

**Files:**
- Create: `src/problem2/audit.py`
- Create: `scripts/preprocess_g2_roads.py`
- Create: `scripts/audit_g2_deterministic.py`
- Create: `tests/g2/test_g2_cli.py`
- Create: `outputs/problem2_sr_mappo_v1/g2/roads/<scale_id>/road_graph.npz` for six scales
- Create: `outputs/problem2_sr_mappo_v1/g2/roads/<scale_id>/metadata.json` for six scales
- Create: `outputs/problem2_sr_mappo_v1/g2/deterministic-event-trace.jsonl`
- Create: `outputs/problem2_sr_mappo_v1/g2/g2-deterministic-audit.json`
- Create: `outputs/problem2_sr_mappo_v1/g2/artifact-manifest.json`

**Interfaces:**
- Consumes: all Task 1-6 interfaces and the frozen real GraphML source.
- Produces: `preprocess_all(config, output_root, generator_commit) -> tuple[RoadCacheRecord, ...]`.
- Produces: `run_g2_audit(config, output_root, generator_commit) -> G2AuditReport`.
- Both CLIs return zero only for a complete pass and publish no partial final report on failure.

- [x] **Step 1: Write failing CLI success, corruption, and output-boundary tests**

```python
def test_preprocessor_generates_exactly_six_valid_cache_pairs(tmp_path):
    result = run_preprocessor(config_path=REAL_CONFIG, output_root=tmp_path)
    assert result.returncode == 0
    assert sorted(path.parent.name for path in tmp_path.glob("roads/*/road_graph.npz")) == ALL_SCALE_IDS

def test_audit_returns_nonzero_for_corrupt_cache(tmp_path):
    generate_caches(tmp_path)
    corrupt_first_cache(tmp_path)
    result = run_audit(config_path=REAL_CONFIG, output_root=tmp_path)
    assert result.returncode != 0
    assert not (tmp_path / "g2-deterministic-audit.json").exists()

def test_cli_rejects_output_outside_frozen_root(tmp_path):
    result = run_preprocessor(config_path=REAL_CONFIG, output_root=tmp_path / "forbidden")
    assert result.returncode != 0
    assert "allowed output root" in result.stderr
```

Use an explicit test-only override flag only for pytest temporary directories;
production invocation accepts solely the frozen G2 root.

- [x] **Step 2: Run CLI tests and observe the intended missing-script failure**

Run: `python -m pytest tests/g2/test_g2_cli.py -q`

Expected: tests fail because the CLIs do not exist.

- [x] **Step 3: Implement preprocessing and audit orchestration**

The preprocessor loads/project the source once, rasterizes six scales, writes
and reload-validates each cache, then returns canonical records. The audit
reloads all caches, checks A*/Dijkstra pairs, masks, motion, service fixtures,
conservation, and two hash-seed subprocess traces before atomically publishing
the report and manifest.

- [x] **Step 4: Run CLI tests and full regression**

Run: `python -m pytest tests/g2/test_g2_cli.py -q`

Expected: all CLI tests pass.

Run: `python -m pytest -q`

Expected: the full suite passes.

- [x] **Step 5: Commit code and tests before generating evidence**

```powershell
git add src/problem2/audit.py scripts/preprocess_g2_roads.py scripts/audit_g2_deterministic.py tests/g2/test_g2_cli.py
git commit -m "feat: add fail-closed g2 deterministic audit"
```

Capture this commit as the generator commit. Generate evidence only from this
clean commit so cache metadata has non-circular code provenance. On later audit
runs, resolve the same value with `git log -1 --format=%H -- pyproject.toml
requirements-g2.lock configs/problem2/g2_deterministic.yaml src/problem2
scripts/preprocess_g2_roads.py scripts/audit_g2_deterministic.py`; pure evidence
or documentation commits therefore do not create a false cache invalidation.

- [x] **Step 6: Generate the six real caches and unified audit evidence**

Run:

```powershell
python scripts/preprocess_g2_roads.py --config configs/problem2/g2_deterministic.yaml
python scripts/audit_g2_deterministic.py --config configs/problem2/g2_deterministic.yaml --report outputs/problem2_sr_mappo_v1/g2/g2-deterministic-audit.json
```

Expected: both commands print `status=pass`, identify six scales, and report no
failed invariant. The audit report records the clean generator commit.

- [x] **Step 7: Verify generated artifacts and commit them**

Run: `python -m pytest tests/g2 -q`

Expected: all G2 tests pass against the generated evidence.

Run: `git diff --check`

Expected: no output and exit code zero.

```powershell
git add outputs/problem2_sr_mappo_v1/g2
git commit -m "test: record g2 deterministic evidence"
```

### Task 8: Full Gate Review, Persistence, And Project State

**Files:**
- Modify: `docs/superpowers/plans/2026-08-20-g2-deterministic-validation.md`
- Modify if implementation correction is required: `docs/superpowers/specs/2026-08-20-g2-deterministic-validation-design.md`
- Modify: `docs/PROJECT_STATE.md`
- Create: `HANDOFFG2.md`

**Interfaces:**
- Consumes: the approved spec, completed plan tasks, clean generated evidence, and complete Git history.
- Produces: an auditable G2 acceptance record with pushed content hash, fresh command results, remaining limits, and next authorized gate G3.

- [x] **Step 1: Review every spec requirement against code, tests, and artifacts**

Create a local checklist mapping Sections 3-14 of the spec to production paths,
test names, cache/report fields, and command evidence. Any missing mapping is a
failed G2 requirement and must be repaired through a new failing test before
continuing.

- [x] **Step 2: Run the complete fresh verification sequence**

```powershell
python -m pytest tests/g2 -q
python -m pytest -q
python scripts/preprocess_g2_roads.py --config configs/problem2/g2_deterministic.yaml
python scripts/audit_g2_deterministic.py --config configs/problem2/g2_deterministic.yaml --report outputs/problem2_sr_mappo_v1/g2/g2-deterministic-audit.json
git diff --check
```

Expected: both test commands have zero failures; both CLIs report pass for six
scales; cross-process replay matches; Git whitespace check is clean.

- [x] **Step 3: Record implementation corrections and complete the plan checklist**

If an approved design detail changed for correctness, update the design with
the observed issue, replacement rule, evidence, and scope impact. Mark each
completed plan checkbox only after its recorded RED and GREEN command ran.

- [x] **Step 4: Write the self-contained G2 handoff and pre-persistence state**

`HANDOFFG2.md` must state the branch/base, module and artifact inventory, exact
test/audit results, deterministic limits, protected assets, prohibited claims,
and G3 entry criteria. Update `docs/PROJECT_STATE.md` with G2 status but leave
the pushed content hash field pending until the content commit is pushed.

- [ ] **Step 5: Commit and push the complete G2 content**

```powershell
git add docs/superpowers/plans/2026-08-20-g2-deterministic-validation.md docs/superpowers/specs/2026-08-20-g2-deterministic-validation-design.md docs/PROJECT_STATE.md HANDOFFG2.md outputs/problem2_sr_mappo_v1/g2
git commit -m "docs: record g2 deterministic validation"
git push -u origin codex/problem2-g2-deterministic-validation
```

Verify `git rev-parse HEAD`, `git rev-parse @{upstream}`, and `git ls-remote`
all report the same content commit.

- [ ] **Step 6: Persist the pushed hash and final verification record**

Replace the pending field in `docs/PROJECT_STATE.md` with the verified content
hash and record exact command counts/results. Commit and push:

```powershell
git add docs/PROJECT_STATE.md
git commit -m "docs: persist g2 verification hash"
git push
```

- [ ] **Step 7: Verify the final repository state**

Run:

```powershell
git status --short --branch
git rev-parse HEAD
git rev-parse @{upstream}
git ls-remote origin refs/heads/codex/problem2-g2-deterministic-validation
```

Expected: worktree clean; local HEAD, upstream, and remote branch hashes match.
The authoritative state declares G2 passed at M2 and G3 as the next authorized
gate while training, formal experiments, and sealed tests remain prohibited.
