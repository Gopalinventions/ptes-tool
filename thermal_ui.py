"""Streamlit adapter: explicit assumptions, repeatable inputs, no hidden dispatch."""
import hashlib
import io
import json
from dataclasses import replace
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from thermal_model import Settings, simulate
from thermal_report import thermal_html


def read_profile(frame):
    required=['timestamp','net_charge_kw','discharge_request_kw']
    if any(k not in frame.columns for k in required):
        raise ValueError('CSV needs timestamp, net_charge_kw, discharge_request_kw columns.')
    times=pd.to_datetime(frame['timestamp'],utc=True,errors='raise')
    if times.isna().any() or len(times)<1 or len(times)>8784:
        raise ValueError('Use 1–8784 rows with valid timestamps.')
    if len(times)>1 and not (times.diff().iloc[1:]==pd.Timedelta(hours=1)).all():
        raise ValueError('Timestamps must be consecutive hourly instants, in increasing order; use UTC to avoid daylight-saving duplicates.')
    powers=frame[['net_charge_kw','discharge_request_kw']].apply(pd.to_numeric,errors='raise')
    return list(powers.itertuples(index=False,name=None)),[t.isoformat() for t in times]


def render_thermal(g, hydraulic_power, hydraulic_dt):
    st.subheader('Step 2 · Thermal stratification')
    st.caption('Uses the geometry above automatically. No second volume or depth entry. Simulation is independent of annual-demand sizing and the static utilisation factor.')
    with st.expander('Thermal simulation · conditions and hourly schedule',expanded=False):
        st.warning('Preliminary uncalibrated model. Defaults below are editable examples, not measured Mühlhausen inputs. No heat pump, transient soil domain, inlet jet or heat-exchanger losses are modelled.')
        c1,c2=st.columns(2)
        with c1:
            source=st.number_input('Water entering top during charging [°C]',5.,95.,90.,key='th_source')
            returned=st.number_input('Water returning to bottom during discharge [°C]',5.,95.,40.,key='th_return')
            delivery=st.number_input('Minimum top temperature for direct discharge [°C]',5.,95.,70.,key='th_delivery')
        with c2:
            initial_bottom=st.number_input('Initial bottom temperature [°C]',5.,95.,40.,key='th_initial_bottom')
            initial_top=st.number_input('Initial top temperature [°C]',5.,95.,40.,key='th_initial_top')
            flow=st.number_input('Maximum circulating water flow [m³/h]',.1,value=round(hydraulic_power/(1.163*hydraulic_dt),2),key='th_flow')
        st.caption('Initial temperature varies linearly between the bottom and surface. Flow is initially suggested from the hydraulic design point, then remains your explicit simulation input. Actual flow changes with temperatures and requested power.')
        mode=st.radio('Hourly schedule source',['Demonstration only','Upload hourly CSV'],horizontal=True,key='th_mode')
        times=None; profile=None; label='Demonstration schedule — not measured generation or network demand'
        if mode=='Demonstration only':
            a,b,c=st.columns(3)
            with a:
                charge_days=st.number_input('Charge days',0,366,30,key='th_cd')
            with b:
                idle_days=st.number_input('Idle days',0,366,7,key='th_id')
            with c:
                discharge_days=st.number_input('Discharge days',0,366,30,key='th_dd')
            requested_in=st.number_input('Constant net surplus during charge [kW]',0.,value=float(hydraulic_power),key='th_qin')
            requested_out=st.number_input('Constant requested discharge [kW]',0.,value=float(hydraulic_power),key='th_qout')
            if charge_days+idle_days+discharge_days<=366:
                profile=[(requested_in,0.)]*(24*charge_days)+[(0.,0.)]*(24*idle_days)+[(0.,requested_out)]*(24*discharge_days)
            else:
                st.error('Combined duration must not exceed 366 days.')
        else:
            st.caption('Upload heat available at the storage boundary AFTER direct-network bypass and upstream losses. Do not enter solar nameplate capacity as hourly solar production. Resolve simultaneous charge/discharge requests upstream. Timestamps identify the START of each hourly interval.')
            st.download_button('Download hourly CSV template','timestamp,net_charge_kw,discharge_request_kw\n2025-05-01T00:00:00Z,0,0\n2025-05-01T01:00:00Z,0,0\n','ptes_hourly_template.csv','text/csv')
            upload=st.file_uploader('Hourly storage-boundary powers',type=['csv'],key='th_csv')
            if upload:
                try:
                    profile,times=read_profile(pd.read_csv(io.BytesIO(upload.getvalue())))
                    label=f'User-supplied hourly schedule: {upload.name}; source accuracy not verified'
                except (ValueError,TypeError) as exc:
                    st.error(str(exc))
        st.markdown('**Heat transfer and numerical settings — editable assumptions**')
        a,b,c=st.columns(3)
        with a:
            cover_u=st.number_input('Effective cover U [W/m²K]',0.,value=.15,format='%.3f',key='th_uc')
            side_u=st.number_input('Effective wet-wall U [W/m²K]',0.,value=.10,format='%.3f',key='th_us')
            bottom_u=st.number_input('Effective bottom U [W/m²K]',0.,value=.10,format='%.3f',key='th_ub')
        with b:
            air=st.number_input('Constant external cover temperature [°C]',-40.,60.,10.,key='th_air')
            soil=st.number_input('Constant ground boundary temperature [°C]',5.,60.,10.,key='th_soil')
            conductivity=st.number_input('Effective vertical conductivity [W/mK]',0.,value=.6,key='th_k')
        with c:
            layers=st.selectbox('Number of water layers',[10,20,40,80],index=1,key='th_layers')
            step=st.selectbox('Maximum internal time step [minutes]',[1.,2.5,5.],index=2,key='th_step')
            cap=st.number_input('Storage-interface power limit, each direction [kW]',0.,value=float(hydraulic_power),key='th_cap')
        st.caption('Effective U-values are NOT derived from material labels, insulation thickness or nearby groundwater. The cover term represents an effective water-to-outside boundary; freeboard air and dry upper walls are not separately resolved. Flow/time-step limits are numerical/operational inputs, not proof of pipe capacity.')
        cfg=Settings(layers,initial_bottom,initial_top,source,returned,delivery,flow,cap,cap,cover_u,side_u,bottom_u,air,soil,conductivity,step)
        refine=st.checkbox('Check sensitivity using twice as many layers',value=True,disabled=layers==80,key='th_refine') and layers<80
        st.caption('First-order layer transport can spread the thermocline numerically. A small energy-balance residual does not establish layer-resolution accuracy. Compare layers before using predicted discharge.')
        signature=hashlib.sha256(json.dumps([g,cfg.__dict__,profile,times,label,refine],sort_keys=True).encode()).hexdigest()
        run=st.button('Run thermal stratification',type='primary',disabled=not profile)
        if run:
            try:
                with st.spinner('Solving layer heat balances…'):
                    result=simulate(g,cfg,profile)
                    if refine:
                        fine=simulate(g,replace(cfg,layers=layers*2),profile)
                        base=result['totals']['discharge_mwh']; refined=fine['totals']['discharge_mwh']
                        result['refinement']=dict(base_layers=layers,refined_layers=layers*2,
                                                  base_discharge_mwh=base,refined_discharge_mwh=refined,
                                                  relative_difference_percent=100*abs(base-refined)/max(1.,abs(refined)))
                st.session_state['thermal_run']=(signature,result,label,times)
            except ValueError as exc:
                st.error(str(exc))
    saved=st.session_state.get('thermal_run')
    if not saved:
        st.info('Open thermal simulation, review its assumptions, then run. Network/GIS upload is not required for this calculation.')
        return
    if saved[0]!=signature:
        st.info('Inputs changed. Run the simulation again; previous thermal results are hidden to avoid showing stale geometry or temperatures.')
        return
    _,result,label,times=saved
    totals=result['totals']; rows=result['history']
    refinement=result.get('refinement')
    if refinement:
        message=(f"Layer sensitivity: {refinement['base_layers']} layers delivered {refinement['base_discharge_mwh']:,.1f} MWh; "
                 f"{refinement['refined_layers']} layers delivered {refinement['refined_discharge_mwh']:,.1f} MWh "
                 f"(difference {refinement['relative_difference_percent']:.1f}%, relative to refined result with a 1 MWh denominator floor). "
                 'Displayed charts use the selected base resolution. This checks discharge only, not full temperature-profile convergence.')
        if refinement['relative_difference_percent']>5:
            st.warning(message+' Resolution sensitivity exceeds the illustrative 5% warning threshold; do not treat this as a converged engineering prediction.')
        else:
            st.info(message+' This is a numerical comparison, not physical validation.')
    else:
        st.warning('Layer refinement was not checked for this run. Results are exploratory, not established as resolution-independent.')
    a,b,c=st.columns(3)
    a.metric('Accepted charging heat',f"{totals['charge_mwh']:,.1f} MWh")
    b.metric('Delivered discharge heat',f"{totals['discharge_mwh']:,.1f} MWh")
    c.metric('Net boundary heat loss',f"{sum(totals[k] for k in ('cover_loss_mwh','side_loss_mwh','bottom_loss_mwh')):,.1f} MWh")
    residual=max(abs(r['balance_residual_kwh']) for r in rows)
    if residual>0.001:
        st.warning('Energy-balance residual exceeds 0.001 kWh. Investigate numerical settings before using these results.')
    st.caption(f'Maximum cumulative energy-balance residual: {residual:.6f} kWh. {result["substeps"]:,} internal steps. Balance closure checks conservation, not physical validation.')
    document=thermal_html(result,label)
    components.html(document,height=830,scrolling=True)
    st.download_button('Download thermal animation HTML',document,'ptes_thermal_stratification.html','text/html')
    scalar=pd.DataFrame([{k:v for k,v in r.items() if k!='temperatures_c'} for r in rows])
    scalar['requested_charge_kw']=[0.]+[r[0] for r in result['profile']]
    scalar['requested_discharge_kw']=[0.]+[r[1] for r in result['profile']]
    if times:
        scalar.insert(1,'state_time_utc',[times[0]]+[(pd.Timestamp(t)+pd.Timedelta(hours=1)).isoformat() for t in times])
    st.line_chart(scalar.set_index('hour')[['top_c','mean_c','bottom_c']])
    st.dataframe(scalar,hide_index=True)
    st.caption('Row 0 is the initial state; each later row is an end-of-hour state with energy totals for that preceding hour. Losses are signed: negative values mean heat gained from the boundary. Unserved requests may be limited by power, flow or top temperature. Energy above return is not directly usable network capacity.')
    temperatures=pd.DataFrame([r['temperatures_c'] for r in rows],columns=[f'layer_{i+1:02d}_bottom_to_top_C' for i in range(cfg.layers)])
    export=pd.concat([scalar,temperatures],axis=1)
    st.download_button('Download all hourly results CSV',export.to_csv(index=False),'ptes_thermal_hourly.csv','text/csv')
    st.download_button('Download model inputs and geometry JSON',json.dumps(dict(settings=result['settings'],geometry=g,layers=result['layers'],schedule_label=label,status=result['status'],hourly_profile=result['profile'],interval_start_utc=times,volumetric_heat_capacity_kwh_m3k=1.163,refinement=refinement),indent=2),'ptes_thermal_inputs.json','application/json')
    st.caption('Model reference: TRNSYS multi-node storage principles; independently implemented and not calibrated or certified as equivalent to TRNSYS. https://trnsys.org/MaillistArchive/pdfkSLYr_lzDr.pdf')
