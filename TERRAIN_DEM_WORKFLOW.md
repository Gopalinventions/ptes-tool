# Mühlhausen PTES terrain and elevation work

## Status

No DGM/DEM raster is in this project yet. Existing excavation and embankment
drawings use an ideal, level reference plane. The input called
`Candidate elevation above nearest pipe` is manual; it is not a measured ground level.
Neither the current 2D/3D drawing nor the GIS result is a surveyed earthworks
design.

## Source and site

- Official source: Thüringer Landesamt für Bodenmanagement und Geoinformation
  (TLBG), [Höhendaten download](https://geoportal.geoportal-th.de/gaialight-th/_apps/dladownload/dl-dhm.html).
- Choose **DGM** (bare-ground terrain), not DOM (buildings and vegetation).
- Prefer the newest available 1 m GeoTIFF DGM tile for the actual PTES location.
  Check its accompanying `.meta` file for acquisition date, horizontal and
  vertical CRS, accuracy and quality level. If the newer tile is unavailable,
  record the year and resolution of the older tile used.
- Current *concept centre*: 51.2244036° N, 10.4696495° E from the PTES
  presentation. This is not a surveyed final pit centre.
- Approximate ETRS89 / UTM zone 32 location (EPSG:25832):
  E 602624 m, N 5675806 m. The nominal 1 km tile index is E 602,
  N 5675. Confirm the actual tile selection in the portal; add neighbouring
  tiles if the full construction envelope or access route crosses a tile edge.
- Recent TLBG DGM tiles use 1 m cells in 1 km squares and provide GeoTIFF
  and XYZ versions. The 2020–2025 data guide states ETRS89/UTM32 horizontally
  and DHHN2016 heights in NHN. Never mix these heights with an unverified
  groundwater datum.

TLBG data guide:
[README Höhendaten 2020–2025](https://geoportal.geoportal-th.de/hoehendaten/Uebersichten/README_Hoehendaten_2020-2025.pdf).

## QGIS processing

1. Add the downloaded DGM GeoTIFF tile(s) to QGIS. Open **Layer Properties →
   Information** and record pixel size, horizontal CRS, minimum/maximum
   elevations, NoData value and extent. Retain the source `.meta` file.
2. Overlay the candidate centre, *actual* parcel boundary, planned PTES rim,
   permanent perimeter and temporary construction/access boundary. Confirm
   their position and rotation. Do not create a site-fit conclusion from the
   centre point alone.
3. If several DGM tiles are needed, build a virtual raster. Clip a working
   copy to the investigation area, retaining enough surrounding ground for
   drainage and access assessment. Keep the original tiles unchanged.
4. Produce a hillshade, slope map and contours for understanding the landform.
   Inspect minimum/mean/maximum ground elevation and cross-sections through
   both pit axes and the access route.
5. Export a small, clipped GeoTIFF for the PTES tool, plus a GeoPackage with
   the verified rim, construction and parcel polygons. Keep the source name,
   tile date, CRS and vertical datum with the export.

QGIS reference:
[Raster terrain analysis](https://documentation.qgis.org/3.44/en/docs/user_manual/processing_algs/qgis/rasterterrainanalysis.html).

## PTES calculations after the DGM is available

For each candidate and the *chosen* pit rotation, sample the DGM under the
excavation rim, permanent perimeter and temporary construction area:

- Elevation range and ground slope across each boundary, including coverage
  and NoData checks.
- Longitudinal and transverse existing-ground profiles through the pit centre.
- A proposed rim/crest level and bottom formation level, stated explicitly in
  metres NHN. These levels are design choices, not outputs of the DGM.
- Cell-by-cell excavation and fill from the difference between existing ground
  and the designed 3D formation. Sum cell volumes (height difference × cell
  area), and report cut and fill separately. Include working slopes and
  embankment geometry only after their section details are agreed.
- Preliminary quantities for topsoil stripping, excavation, embankment and
  possible off-site disposal, each clearly separated. Bulking/shrinkage,
  unsuitable soil and groundwater dewatering require geotechnical inputs.
- Compare bottom formation and drainage levels with *site-relevant* monitored
  groundwater levels after confirming both datasets use the same height datum.
  The existing Ammern observation is context, not a PTES-site groundwater
  measurement.
- Use terrain elevation at the actual network connection point and PTES pump
  location for a revised static head check; the DEM alone cannot determine
  operating supply/return pressures or pipe losses.

## Outputs to add to the Streamlit tool

1. A visible data register: raster source, acquisition date, cell size,
   CRS/datum, coverage and quality notes.
2. One map with DGM hillshade/contours and the 125,000 m³ design envelopes.
3. Dimensioned 2D sections showing both existing terrain and proposed PTES
   levels; clearly label cut and fill.
4. A 3D terrain surface with the pit geometry positioned against measured
   ground levels. Label vertical exaggeration, if used.
5. An Excel sheet with candidate elevations, area, cut/fill volumes and the
   assumptions used for the design levels.

The current 2D/3D browser rendering problem should be repaired separately;
adding terrain will not by itself make the existing design view display.
