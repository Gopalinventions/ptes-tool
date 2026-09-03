# PTES Location Screening and Design Tool

This Streamlit project converts the PTES notebook into a web application. It uploads an nPro GeoJSON, detects buildings and pipes, lets the user click a candidate location, and performs preliminary thermal, hydraulic and spatial screening.

## Project files

- `app.py`: Streamlit user interface
- `calculations.py`: capacity, flow, DN, pressure-loss and scoring calculations
- `gis_analysis.py`: GeoJSON, CRS, demand and nearest-pipe operations
- `spatial_analysis.py`: parcel, constraint, road, utility and groundwater measurements
- `requirements.txt`: Python packages
- `.streamlit/config.toml`: colours and upload settings

## Run on Windows

The recommended method is a dedicated Conda environment. Open Anaconda Prompt in this folder:

```powershell
conda env create -f environment.yml
conda activate ptes-tool
streamlit run app.py
```

Streamlit should open `http://localhost:8501`. Stop it with `Ctrl+C`.

Do not install these packages into the Anaconda `base` environment. If the environment already exists, update it with:

```powershell
conda env update -f environment.yml --prune
conda activate ptes-tool
streamlit run app.py
```

## Use the app

1. Upload the nPro `.geojson` or `.json` file.
2. Select the annual heat-demand column (MWh/year).
3. Optionally upload authoritative parcel, groundwater, flood, protected-area, road and utility GeoJSON layers.
4. Enter PTES demand, operating and boundary-clearance inputs.
5. Place up to three candidate locations and optionally draw multi-bend connection routes.
6. Click **Analyse and compare**.
7. Review the measured boundaries, hydraulic screening, constraint intersections and data register.
8. Download the interactive HTML map, candidate CSV and GIS data register.

## Publish with Streamlit Community Cloud

1. Create a GitHub repository and upload this folder.
2. Sign in at `https://share.streamlit.io` with GitHub.
3. Select **Create app** and choose the repository.
4. Set the entrypoint to `app.py` and deploy.

Do not put confidential network data in a public repository. The application does not contain a GeoJSON file; users upload data at runtime.

## Engineering scope

This is preliminary engineering screening, not final design. Missing authority datasets are marked **Not assessed**; the app does not invent groundwater, flood, protected-area, road or utility values. Pipe dimensions are representative and the pressure-loss result uses assumed Darcy-Weisbach parameters. Validate survey elevations, groundwater time series, network topology, pumps, boundary pressures, pipe roughness, fittings, transient cases and permits before design approval.
