# Preliminary thermal stratification · version 1

## Input separation

- Section 2 sets water volume and pit depth; advanced geometry adds freeboard, slope and bottom aspect ratio. These determine GIS rim, drawings and water layers together.
- Section 2b provides annual network demand/context and an optional **static** capacity estimate. Its hot/cold reference temperatures and utilisation factor are not an hourly simulation or inferred round-trip efficiency.
- Section 3 is the **hydraulic design point** used for pipe sizing/pressure screening. Its supply–return ΔT differs from the stored-water hot/cold span. Mode does not prescribe a seasonal schedule.
- Main-page Step 2 runs thermal operation: initial temperature profile, charging inlet temperature, discharge return temperature, minimum direct-supply temperature, actual flow/power limits, schedule and heat-transfer assumptions.

The thermal model never multiplies results by the static utilisation factor. Changing any model input or geometry hides stale thermal results until another run. Flow and interface-power widget defaults are initial suggestions, not continuously imposed pipeline limits.

## Geometry and heat balance

For bottom dimensions b,l, slope s and water height z, integrated volume is
V(z) = b*l*z + s*(b+l)*z² + 4*s²*z³/3.
Water height is total depth minus freeboard. Equal-height nodes use V(z1)−V(z0), not equal volumes. Side areas follow the sloped wetted walls. Freeboard dry walls and air are not explicitly solved.

Each node satisfies C_i dT_i/dt = advected heat + interlayer conduction − boundary heat loss.
Constant C_i = 1.163 V_i kWh/K is an approximation. Temperature-dependent density and heat capacity are not included. Bottom-to-top layer numbering is used in every CSV. Upwind finite-volume advection preserves energy but introduces numerical diffusion; layer/time-step refinement is required before interpreting thermocline thickness.

Charging: source water enters the top, storage water exits the bottom. Discharge: water exits the top and specified return water enters the bottom. Volume remains fixed. Thermal power is limited by both available/requested heat and circulation capacity. Direct discharge is disabled below the minimum top-node delivery temperature. There is no heat-pump-assisted extraction or heat-exchanger approach-temperature model.

Conduction uses effective k*A/dz. Inverted adjacent layers are pooled until temperature increases upwards, conserving heat. This is a simplified buoyancy treatment valid for the supported water-temperature range above 4 °C, not a calibrated inlet mixing or turbulence model.

Signed losses are U*A*(T_water−T_boundary), split into cover, wetted side walls and bottom. **Default U-values (0.15/0.10/0.10 W/m²K), boundary temperatures (10 °C), conductivity (0.6 W/mK), inlet/return temperatures and schedules are editable illustrative inputs, not site measurements.** The material quantity inputs do not determine thermal U-values automatically. Soil warming, groundwater advection, cover moisture/air, thermal bridges and evolving weather are not solved.

Explicit substeps are at most the selected 1–5 minutes and are reduced to keep each outgoing coefficient below 20% of node heat capacity per step. Cumulative energy balance includes initial energy, charge, discharge and signed boundary loss. A small residual demonstrates conservation only, not physical validation.

## Schedules and exports

Demonstration: constant charge power, idle, then constant discharge request, with editable durations. This is not solar availability or calibrated BHKW dispatch.

CSV: `timestamp,net_charge_kw,discharge_request_kw`, one consecutive hourly interval per row (timestamp marks interval start). Use UTC/explicit offsets; naive timestamps are interpreted as UTC. Maximum 8784 records. Net charge must already account for direct-network bypass and upstream losses. Negative, nonfinite or simultaneous positive charge/discharge requests are rejected. No synthetic netting conceals generation/demand accounting.

Row zero is initial state. Later rows contain end-of-hour temperatures and preceding-interval heat totals. Unaccepted surplus and unserved discharge requests are separately recorded. Energy above return temperature is NOT automatically directly deliverable network heat. No efficiency percentage is inferred from a partially charged/discharged period.

Outputs: hourly/layer CSV, complete model-input/geometry/profile JSON, and offline temperature animation HTML with 2D section and idealised 3D layers. Display in 3D does not make the solver a 3D CFD calculation.

## Verification and next validation

Tests cover layer geometry, adiabatic idle/charging, heat balance including losses/conduction, mixing conservation, discharge cutoff and analytical uniform cooling. Before engineering use, compare 10/20/40/80 nodes and smaller time steps; calibrate heat-transfer/mixing parameters against measured project data. Add transient surrounding soil, actual hourly boundary temperatures, validated heat-exchanger and heat-pump performance only as separate verified extensions.

Reference for multi-node model principles (not copied software and not claimed equivalent):
https://trnsys.org/MaillistArchive/pdfkSLYr_lzDr.pdf
https://www.trnsys.com/assets/docs/03-ComponentLibraryOverview.pdf

## Deployment

Upload the changed `app.py` and new `thermal_model.py`, `thermal_ui.py`, `thermal_report.py`, plus `designer_assets/thermal.html` in that exact folder. Preserve the existing designer assets and GIS modules. No new package dependency is introduced. Tests: `python -m unittest test_thermal_model.py test_designer_integration.py`.
