"""Offline thermal animation export without Streamlit dependencies."""
import json
from pathlib import Path


def thermal_html(result, label):
    label += ' | Preliminary, uncalibrated model. Compare layer resolutions before using discharge predictions.'
    sensitivity=result.get('refinement')
    if sensitivity:
        label += (f" | {sensitivity['base_layers']} versus {sensitivity['refined_layers']} layers: "
                  f"discharge difference {sensitivity['relative_difference_percent']:.1f}%. Charts show base resolution.")
    payload=dict(geometry=result['geometry'],layers=result['layers'],label=label,
                 history=[{k:v for k,v in row.items() if k in ('hour','top_c','bottom_c','energy_above_return_mwh','temperatures_c')} for row in result['history']])
    return Path(__file__).with_name('designer_assets').joinpath('thermal.html').read_text(encoding='utf-8').replace(
        '__THERMAL_DATA__',json.dumps(payload,allow_nan=False).replace('<','\\u003c'))
