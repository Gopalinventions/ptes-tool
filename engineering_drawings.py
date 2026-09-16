"""Static, Streamlit-safe preliminary PTES engineering drawings.

The drawings intentionally use the same parametric geometry as the energy and
GIS modules.  They are concept drawings, not construction documents.
"""
from __future__ import annotations

from html import escape


NAVY = "#102a43"
BLUE = "#1e88b5"
WATER = "#52b6d9"
EARTH = "#a66c45"
LINER = "#ef6c00"
GREEN = "#4caf50"
GREY = "#64748b"


def _f(value: float) -> str:
    return f"{float(value):,.1f}"


def _svg(body: str, width: int = 1200, height: int = 720) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Preliminary PTES engineering drawing">
    <style>
    text {{ font-family: Arial, sans-serif; fill: {NAVY}; }} .title {{ font-size:22px;font-weight:bold }}
    .sub {{ font-size:12px }} .label {{ font-size:13px }} .dim {{ font-size:12px;fill:#36546d }}
    .line {{ stroke:{NAVY};stroke-width:1.5;fill:none }} .thin {{ stroke:#78909c;stroke-width:1;fill:none }}
    .dash {{ stroke:#78909c;stroke-width:1;stroke-dasharray:5 4;fill:none }}
    </style><rect width="100%" height="100%" fill="white"/>{body}</svg>'''


def engineering_schedule(inputs: dict, model: dict):
    """A compact shared register for drawings and Excel exports."""
    layout = inputs.get("layout", {})
    return [
        ("Design status", "Preliminary concept — not for construction"),
        ("Water volume", f"{_f(model['waterVolume'])} m³"),
        ("Pit depth / water depth", f"{_f(model['H'])} m / {_f(model['h'])} m"),
        ("Freeboard", f"{_f(model['f'])} m"),
        ("Side slope H:V", f"{_f(model['s'])}:1"),
        ("Rim footprint", f"{_f(model['L'])} × {_f(model['B'])} m"),
        ("Water surface", f"{_f(model['wl'])} × {_f(model['wb'])} m"),
        ("Bottom", f"{_f(model['l'])} × {_f(model['b'])} m"),
        ("Cover area", f"{_f(model['coverArea'])} m²"),
        ("Liner order area", f"{_f(model['linerOrderArea'])} m²"),
        ("Permanent perimeter", f"{_f(inputs.get('permanentPerimeter', 0))} m"),
        ("Temporary working envelope", f"{_f(inputs.get('temporaryWorking', 0))} m"),
        ("Pump chamber", f"{layout.get('pumpSide', 'East')} side; {_f(layout.get('pumpLength', 0))} × {_f(layout.get('pumpWidth', 0))} m"),
        ("Drainage wells", str(layout.get('drainageWells', 0))),
        ("Indicative design flow", f"{_f(layout.get('designFlowM3h', 0))} m³/h"),
    ]


def plan_svg(inputs: dict, m: dict) -> str:
    perimeter = inputs.get("permanentPerimeter", 0)
    working = inputs.get("temporaryWorking", 0)
    # Drawing scale applies only to this plan view.
    scale = min(650 / (m['L'] + 2 * (perimeter + working)), 430 / (m['B'] + 2 * (perimeter + working)))
    cx, cy = 400, 385
    def rect(l, b, style):
        x, y = cx - l * scale / 2, cy - b * scale / 2
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{l*scale:.1f}" height="{b*scale:.1f}" {style}/>'
    rim = rect(m['L'], m['B'], 'fill="#f8fafc" stroke="#102a43" stroke-width="2"')
    water = rect(m['wl'], m['wb'], f'fill="{WATER}" fill-opacity=".55" stroke="{BLUE}" stroke-width="2"')
    bottom = rect(m['l'], m['b'], 'fill="none" stroke="#a66c45" stroke-width="1.5" stroke-dasharray="5 3"')
    envelope = rect(m['L'] + 2*(perimeter+working), m['B'] + 2*(perimeter+working), 'fill="none" stroke="#78909c" stroke-width="1" stroke-dasharray="7 4"')
    permanent = rect(m['L'] + 2*perimeter, m['B'] + 2*perimeter, 'fill="none" stroke="#4caf50" stroke-width="1.3" stroke-dasharray="4 3"')
    layout = inputs.get('layout', {})
    pump_l, pump_w = layout.get('pumpLength', 10), layout.get('pumpWidth', 6)
    px = cx + m['L']*scale/2 + perimeter*scale/2
    pump = f'<rect x="{px:.1f}" y="{cy-pump_w*scale/2:.1f}" width="{pump_l*scale:.1f}" height="{pump_w*scale:.1f}" fill="#dbeafe" stroke="{NAVY}"/><text class="label" x="{px+pump_l*scale/2:.1f}" y="{cy+4:.1f}" text-anchor="middle">Pump chamber</text>'
    pipe = f'<path d="M {px:.1f} {cy:.1f} L {cx+m["wl"]*scale/2:.1f} {cy:.1f}" stroke="#d32f2f" stroke-width="5" fill="none"/><path d="M {cx+m["wl"]*scale/2:.1f} {cy:.1f} L {cx:.1f} {cy:.1f}" stroke="#1565c0" stroke-width="4" stroke-dasharray="7 4" fill="none"/>'
    wells = ''.join(f'<circle cx="{cx + dx*m["L"]*scale/2:.1f}" cy="{cy + dy*m["B"]*scale/2:.1f}" r="5" fill="#37474f"/><text class="sub" x="{cx + dx*m["L"]*scale/2+8:.1f}" y="{cy + dy*m["B"]*scale/2+4:.1f}">DW</text>' for dx,dy in [(-.82,-.82),(.82,-.82),(-.82,.82),(.82,.82)][:int(layout.get('drainageWells', 0))])
    return _svg(f'''
    <text class="title" x="35" y="38">GENERAL ARRANGEMENT / PLAN</text><text class="sub" x="35" y="58">PTES parametric concept — preliminary design, not for construction</text>
    {envelope}{permanent}{rim}{water}{bottom}{pipe}{pump}{wells}
    <path class="dash" d="M {cx-360} {cy} H {cx+360} M {cx} {cy-250} V {cy+250}"/>
    <text class="label" x="{cx}" y="{cy-10}" text-anchor="middle">Floating insulated cover / water surface</text>
    <text class="sub" x="{cx}" y="{cy+15}" text-anchor="middle">Top / middle / bottom diffuser concept</text>
    <path class="thin" d="M {cx-m['L']*scale/2} {cy+m['B']*scale/2+35} H {cx+m['L']*scale/2}"/>
    <path class="thin" d="M {cx-m['L']*scale/2} {cy+m['B']*scale/2+30} v10 M {cx+m['L']*scale/2} {cy+m['B']*scale/2+30} v10"/>
    <text class="dim" x="{cx}" y="{cy+m['B']*scale/2+53}" text-anchor="middle">{_f(m['L'])} m rim length</text>
    <path class="thin" d="M {cx-m['L']*scale/2-35} {cy-m['B']*scale/2} V {cy+m['B']*scale/2}"/>
    <text class="dim" x="{cx-m['L']*scale/2-43}" y="{cy}" text-anchor="middle" transform="rotate(-90 {cx-m['L']*scale/2-43} {cy})">{_f(m['B'])} m rim width</text>
    <text class="label" x="820" y="120">GEOMETRY REGISTER</text>{''.join(f'<text class="sub" x="820" y="{150+i*25}">{escape(k)}: {escape(v)}</text>' for i,(k,v) in enumerate(engineering_schedule(inputs,m)[:10]))}
    <text class="sub" x="35" y="680">Legend: blue = water/cover footprint; orange dashed = bottom; green dashed = permanent perimeter; grey dashed = temporary working envelope; DW = drainage well.</text>''')


def section_svg(inputs: dict, m: dict) -> str:
    # Longitudinal section uses lengths; cross-section is same calculation using widths.
    def one_section(x0, top, water, bottom, title):
        s = min(430/top, 330/m['H']); base_y = 560; rim_y = base_y-m['H']*s
        left, right = x0, x0+top*s; wl_left=(x0+(top-water)*s/2); wl_right=right-(top-water)*s/2
        bot_left=(x0+(top-bottom)*s/2); bot_right=right-(top-bottom)*s/2; water_y=base_y-m['h']*s
        return f'''<text class="label" x="{x0+top*s/2:.1f}" y="100" text-anchor="middle">{title}</text>
        <path d="M {left} {rim_y} L {right} {rim_y} L {bot_right} {base_y} L {bot_left} {base_y} Z" fill="{EARTH}" fill-opacity=".25" stroke="{EARTH}" stroke-width="2"/>
        <path d="M {wl_left} {water_y} L {wl_right} {water_y} L {bot_right} {base_y} L {bot_left} {base_y} Z" fill="{WATER}" fill-opacity=".65"/>
        <path d="M {wl_left} {water_y} L {wl_right} {water_y}" stroke="#475569" stroke-width="10"/><text class="sub" x="{x0+top*s/2:.1f}" y="{water_y-12:.1f}" text-anchor="middle">floating insulated cover</text>
        <path d="M {left} {rim_y} L {bot_left} {base_y} L {bot_right} {base_y} L {right} {rim_y}" fill="none" stroke="{LINER}" stroke-width="3"/>
        <path d="M {x0-22} {rim_y} V {base_y}" class="thin"/><text class="dim" x="{x0-30}" y="{(rim_y+base_y)/2:.1f}" transform="rotate(-90 {x0-30} {(rim_y+base_y)/2:.1f})" text-anchor="middle">{_f(m['H'])} m pit depth</text>
        <path d="M {bot_left} {base_y+28} H {bot_right}" class="thin"/><text class="dim" x="{(bot_left+bot_right)/2:.1f}" y="{base_y+45}" text-anchor="middle">{_f(bottom)} m bottom</text>
        <path d="M {left} {rim_y-25} H {right}" class="thin"/><text class="dim" x="{(left+right)/2:.1f}" y="{rim_y-32}" text-anchor="middle">{_f(top)} m rim</text>
        <text class="sub" x="{left+20}" y="{rim_y+75}">slope {_f(m['s'])}:1</text><text class="sub" x="{left+20}" y="{rim_y+93}">freeboard {_f(m['f'])} m</text>
        <path d="M {bot_left+15} {base_y-25} H {bot_right-15}" stroke="#1565c0" stroke-width="5"/><text class="sub" x="{(bot_left+bot_right)/2:.1f}" y="{base_y-35}" text-anchor="middle">bottom diffuser / return</text>'''
    return _svg(f'''<text class="title" x="35" y="38">PTES SECTIONS — EXCAVATION, LINER, COVER AND HYDRAULIC CONCEPT</text>
    <text class="sub" x="35" y="58">All levels are local geometry datum only. Surveyed ground levels, groundwater and structural details are required before construction.</text>
    {one_section(70,m['L'],m['wl'],m['l'],'SECTION A–A · length')}{one_section(670,m['B'],m['wb'],m['b'],'SECTION B–B · width')}
    <text class="sub" x="35" y="675">Concept components: protective geotextile + membrane/liner; floating insulated cover; top/middle/bottom hydraulic openings; drainage collection at low points. Final component detail requires civil, geotechnical and supplier design.</text>''')


def isometric_svg(inputs: dict, m: dict) -> str:
    # Isometric, deliberately schematic—not an unverified terrain model.
    cx, cy, sx, sy, dz = 555, 315, 3.4, 1.55, 18
    def pt(x,y,z=0): return (cx+(x-y)*sx, cy+(x+y)*sy-z*dz)
    def poly(points, fill, stroke=NAVY): return '<polygon points="'+' '.join(f'{a:.1f},{b:.1f}' for a,b in points)+f'" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    L,B,l,b,H,h = m['L']/2,m['B']/2,m['l']/2,m['b']/2,m['H'],m['h']
    rim=[pt(-L,-B),pt(L,-B),pt(L,B),pt(-L,B)]
    bottom=[pt(-l,-b,H),pt(l,-b,H),pt(l,b,H),pt(-l,b,H)]
    water=[pt(-m['wl']/2,-m['wb']/2,H-h),pt(m['wl']/2,-m['wb']/2,H-h),pt(m['wl']/2,m['wb']/2,H-h),pt(-m['wl']/2,m['wb']/2,H-h)]
    faces=''.join(poly([rim[i],rim[(i+1)%4],bottom[(i+1)%4],bottom[i]], EARTH if i<2 else '#bc8a66') for i in range(4))
    return _svg(f'''<text class="title" x="35" y="38">3D PTES CONCEPT — PARAMETRIC CUTAWAY</text><text class="sub" x="35" y="58">Schematic geometry generated from the active storage volume, depth, slope and freeboard.</text>
    {faces}{poly(bottom,'#84563d')}{poly(water,WATER,BLUE)}
    <path d="M {water[0][0]:.1f} {water[0][1]:.1f} L {water[1][0]:.1f} {water[1][1]:.1f} L {water[2][0]:.1f} {water[2][1]:.1f} L {water[3][0]:.1f} {water[3][1]:.1f} Z" fill="none" stroke="#475569" stroke-width="8"/>
    <path d="M {water[1][0]:.1f} {water[1][1]:.1f} L {water[1][0]+110:.1f} {water[1][1]-35:.1f}" stroke="#d32f2f" stroke-width="6"/><text class="label" x="{water[1][0]+120:.1f}" y="{water[1][1]-40:.1f}">energy hub / pump connection</text>
    <text class="label" x="70" y="140">Water volume</text><text class="title" x="70" y="170">{_f(m['waterVolume'])} m³</text>
    <text class="label" x="70" y="220">Hydraulic concept</text><text class="sub" x="70" y="243">Hot supply from upper level</text><text class="sub" x="70" y="263">Return / charge via lower diffuser</text>
    <text class="label" x="70" y="320">Civil concept</text><text class="sub" x="70" y="343">uniform {_f(m['s'])}:1 side slopes</text><text class="sub" x="70" y="363">{_f(m['f'])} m freeboard</text><text class="sub" x="70" y="383">liner + cover shown schematically</text>
    <text class="sub" x="35" y="680">This is an engineering communication model, not a survey-based terrain or construction model. Import a DEM and geotechnical data before using it for cut/fill, groundwater, stability or drainage decisions.</text>''')


def standalone_html(inputs: dict, m: dict) -> str:
    """One self-contained offline report; no JavaScript or external assets."""
    return '<!doctype html><html><head><meta charset="utf-8"><title>PTES engineering drawings</title><style>body{margin:20px;background:#edf2f7;font-family:Arial}section{background:white;margin:16px 0;padding:10px;box-shadow:0 1px 4px #9aa}</style></head><body><h1>PTES engineering drawing package</h1><p>Preliminary concept — not for construction.</p><section>'+plan_svg(inputs,m)+'</section><section>'+section_svg(inputs,m)+'</section><section>'+isometric_svg(inputs,m)+'</section></body></html>'
