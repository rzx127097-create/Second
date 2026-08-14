# External Evidence Search Log (2026-08-15)

## Scope and routing

The search covered two separate evidence classes:

1. manufacturer/public product specifications for the UAV and ground support
   hardware;
2. peer-reviewed papers for spray deposition, wind sensitivity, locust
   toxicity and operational calibration.

OpenAlex was used for structured academic discovery, followed by the linked
publisher or official product page where accessible. The public product pages
were read directly; an abstract or specification page is recorded as metadata
and scope evidence only, not as a substitute for a field calibration record.

## Product evidence checked

| Source | Directly reported value | Permitted use in this project |
|---|---:|---|
| DJI T40 official specifications | 40 L tank, 12 L/min maximum pump flow, 7 m/s example operation speed, 10 m/s maximum operation speed | UAV engineering reference and explicit scene-scale conversion |
| DigitalAgro DroneFiller | 500 L tanks, 20 L premix tank, 8 m hose reel, 50 L drone refuelling in under 60 s | Ground-support inventory and hose/transfer reference range |
| FarmChem BatchMate Direct | Two 60 gal mix tanks, up to 41 gpm drone pump | Independent upper-bound transfer-capacity reference |
| Frost DroneMAX | 150 gal product tank, 12 gpm drone pump, 9 gpm clean-water transfer pump | Conservative transfer-rate reference: 12 gpm = 0.7568 L/s |

The latter three products are stationary skids or trailer systems rather than
the exact road vehicle in the simulator. Their values are therefore recorded
with an explicit scene-scale conversion and a vehicle-match blocker. They do
not justify the exact service setup time, vehicle road speed or rendezvous
safety radius.

## Academic records checked

- Zhang et al. (2022), *Toxins*, 14(8), 546,
  [10.3390/toxins14080546](https://doi.org/10.3390/toxins14080546): laboratory
  bioassays on outbreaking Acrididae; supports a species-, life-stage- and
  compound-specific mortality calibration protocol, not this model's `mu_c`.
- Mullié et al. (2023), *Agronomy*, 13(3), 819,
  [10.3390/agronomy13030819](https://doi.org/10.3390/agronomy13030819):
  operational desert-locust insecticide use and environmental-monitoring
  context; it does not provide a transferable local mortality or residue
  coefficient.
- Grant et al. (2022), *Drones*, 6(8), 204,
  [10.3390/drones6080204](https://doi.org/10.3390/drones6080204): wind-tunnel
  spray-drift experiment at 1.5, 3.0 and 4.5 m/s and 2/10 L payloads; it gives
  a spray-application sensitivity range but not a regional field-wind series.
- Chen et al. (2020), Qin et al. (2018), Lan et al. (2021), Biglia et al.
  (2022) and Grella et al. (2017) remain in the ledger for deposition and drift
  mechanisms. Their crop, nozzle and canopy conditions are not silently
  transferred to locust mortality or residue coefficients.

## Search conclusions

The search closes the evidence gap for **reference hardware ranges**, but not
for the project-specific operating point. The following records are still
required before a formal sealed test:

1. emptying/usable-volume test for the selected UAV and formulation;
2. mobile-vehicle tank and service-pump specification or timed transfer test;
3. measured service setup and connection time;
4. road speed under the selected road-surface and payload condition;
5. measured air-ground connection envelope and safety procedure;
6. field wind time series paired to the simulation interval;
7. compound- and crop-specific residue curve and exposure-mortality bioassay;
8. numerical convergence record for `decision_dt` at `dt`, `dt/2` and `dt/4`.

Until these records are attached, the repository remains at M2 and the wording
“mechanistic pilot model with sourced hardware reference ranges” is permitted;
“field-calibrated” and “formal experiment demonstrates efficacy” are not.
