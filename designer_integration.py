"""Shared preliminary geometry for GIS footprints and the embedded drawing studio."""
import json
import math
from pathlib import Path


def design_geometry(target, depth, slope, freeboard, ratio, layout=None, **materials):
    p = dict(mode="volume", target=target, depth=depth, slope=slope,
             freeboard=freeboard, ratio=ratio, length=132, width=120,
             linerThickness=2., linerDensity=940., allowance=5.,
             coverThickness=240., coverDensity=30.,
             permanentPerimeter=5., temporaryWorking=8.)
    p.update(materials)
    for key, value in p.items():
        if key == "mode":
            continue
        if not math.isfinite(value) or value < 0 or (value == 0 and key not in ("slope", "freeboard", "allowance")):
            raise ValueError(f"Invalid geometry/material value: {key}")
    H, s, f = depth, slope, freeboard
    if f >= H:
        raise ValueError("Freeboard must be smaller than total pit depth.")
    h = H-f
    def volume(b, l, z):
        return b*l*z+s*(b+l)*z*z+4*s*s*z**3/3
    if target <= volume(0, 0, h):
        raise ValueError("Target volume is too small for this depth and slope.")
    lo, hi = 0., max(1., math.sqrt(target/h/ratio))
    while volume(hi, ratio*hi, h) < target:
        hi *= 2
    for _ in range(90):
        mid = (lo+hi)/2
        if volume(mid, ratio*mid, h) < target:
            lo = mid
        else:
            hi = mid
    b = (lo+hi)/2
    l = ratio*b
    L, B, wl, wb = l+2*s*H, b+2*s*H, l+2*s*h, b+2*s*h
    side = (l+L+b+B)*H*math.sqrt(1+s*s)
    liner, cover = l*b+side, wl*wb
    order = liner*(1+p['allowance']/100)
    g = dict(H=H, s=s, f=f, h=h, l=l, b=b, L=L, B=B, wl=wl, wb=wb,
             waterVolume=volume(b,l,h), pitVolume=volume(b,l,H), bottomArea=l*b,
             sideArea=side, linerArea=liner, coverArea=cover, linerOrderArea=order,
             linerMass=order*p['linerThickness']/1000*p['linerDensity'],
             insulationVolume=cover*p['coverThickness']/1000,
             insulationMass=cover*p['coverThickness']/1000*p['coverDensity'])
    footprint = dict(top_length_m=L, top_width_m=B, top_area_m2=L*B,
                     bottom_length_m=l, bottom_width_m=b, bottom_area_m2=l*b, depth_m=H)
    # Layout items are deliberately separate from geometry/material validation: they
    # are preliminary operational symbols rather than civil-design quantities.
    p["layout"] = layout or {}
    return p, g, footprint


def designer_html(inputs, model):
    """Offline HTML; geometry is locked to app inputs, appearance remains interactive."""
    assets = Path(__file__).with_name("designer_assets")
    html = (assets/"index.html").read_text(encoding="utf-8")
    payload = json.dumps(dict(inputs=inputs, model=model), allow_nan=False).replace("<", "\u003c")
    geometry_tag = '<script src="geometry.js"></script>'
    if geometry_tag not in html:
        raise RuntimeError("PTES HTML template is missing its embedded-data marker.")
    html = html.replace(geometry_tag, f'<script>window.PTES_EMBEDDED={payload};</script>', 1)
    for name in ("cad.js", "designer.js"):
        script = (assets/name).read_text(encoding="utf-8")
        marker = f'<script src="{name}"></script>'
        if marker not in html or not script.strip():
            raise RuntimeError(f"PTES HTML export could not include {name}.")
        # Split once at the known asset marker instead of using a template
        # replacement. This is robust when the embedded JavaScript contains
        # special characters while Streamlit Cloud builds the download file.
        before, after = html.split(marker, 1)
        html = before + "<script>" + script + "</script>" + after
    if "function update(" not in html or "const CAD=" not in html:
        raise RuntimeError("PTES HTML export is incomplete; no blank design file was created.")
    return html
