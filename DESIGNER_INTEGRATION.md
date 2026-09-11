# Linked PTES designer

The Streamlit app now includes the dimensioned 2D/3D studio before the network upload gate. Start with target water volume and total depth. Advanced geometry contains freeboard, uniform side slope and **bottom** length/width ratio. Other inputs are grouped in collapsed sections. Colour controls inside the 3D view change appearance only; they do not represent temperature or material approval.

`designer_integration.py` computes the shared model. GIS uses its rim dimensions, centred at the selected candidate and rotated in the metric CRS. Drawing coordinates remain local, aligned to the pit axes. The embedded view locks geometry to the sidebar inputs to prevent disagreement with the map; standalone `outputs/ptes-designer` remains independently editable.

Water volume is integrated exactly: V = b*l*h + s*(b+l)*h² + (4/3)*s²*h³, where h = total depth − freeboard, b/l are bottom dimensions and s is H:V. A bisection solve finds bottom dimensions for the requested volume. This replaces the older app-only approximate frustum geometry for this workflow. Existing saved outputs may therefore differ, especially because freeboard is now explicit.

Map embankment and access offsets remain screening buffers. No surveyed excavation quantities, actual terrain model, slope stability, groundwater interpolation, thermal simulation or construction approval is supplied. The 2D sheets and 3D view show ideal geometry; nearby GIS features remain in the existing map. Material defaults are illustrative. No CO₂ factors or TRNSYS results are invented.

## Deployment files

Keep these together in the GitHub repository beside existing calculations/GIS/weather modules:

- app.py
- designer_integration.py
- designer_assets/index.html
- designer_assets/designer.js
- designer_assets/cad.js

No new dependency is required. The HTML is bundled offline and offered as a download. The app embeds it using the existing Streamlit v1 HTML component API. The source designer and bundled assets must be updated together if edited later. This change does not publish anything automatically.

## Checks

Run `python -m unittest test_designer_integration.py` from this folder. Tests cover volumes, exact integral, GIS dimension agreement, invalid designs and offline HTML bundling. Browser checks additionally verify rendering, rotation and colour controls. Future development: verified material/product inputs and construction LCA, then a separately validated dynamic stratified thermal model.
