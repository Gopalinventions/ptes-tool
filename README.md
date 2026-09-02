# PTES Location Screening and Design Tool

This Streamlit project converts the PTES notebook into a web application. It uploads an nPro GeoJSON, detects buildings and pipes, lets the user click a candidate location, and performs preliminary thermal, hydraulic and spatial screening.

## Project files

- `app.py`: Streamlit user interface
- `calculations.py`: capacity, flow, DN, pressure-loss and scoring calculations
- `gis_analysis.py`: GeoJSON, CRS, demand and nearest-pipe operations
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
3. Enter PTES design and land values in the sidebar.
4. Click the proposed PTES location on the map.
5. Click **Run PTES analysis**.
6. Review and download the results.

## Publish with Streamlit Community Cloud

1. Create a GitHub repository and upload this folder.
2. Sign in at `https://share.streamlit.io` with GitHub.
3. Select **Create app** and choose the repository.
4. Set the entrypoint to `app.py` and deploy.

Do not put confidential network data in a public repository. The application does not contain a GeoJSON file; users upload data at runtime.

## Engineering scope

This is preliminary screening, not final design. Pipe dimensions are representative and the pressure-loss result uses assumed Darcy-Weisbach parameters. Validate inputs, materials, fittings and operating cases before design approval.
