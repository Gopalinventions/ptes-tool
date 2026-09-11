"""Preliminary 1-D finite-volume PTES model, not a TRNSYS implementation.

Bottom-to-top nodes; exact sloped-pit layer volumes; conservative upwind
advection; conduction; fixed-boundary UA losses; buoyancy mixing above 4 C.
Constant volumetric heat capacity 1.163 kWh/(m3 K). No soil-domain solution,
heat exchanger approach, inlet jets, heat pumps or calibrated mixing model.
"""
from dataclasses import asdict, dataclass
import math

CV = 1.163


@dataclass(frozen=True)
class Settings:
    layers: int = 20
    initial_bottom_c: float = 40.
    initial_top_c: float = 40.
    source_c: float = 90.
    return_c: float = 40.
    minimum_delivery_c: float = 70.
    max_flow_m3_h: float = 100.
    max_charge_kw: float = 3300.
    max_discharge_kw: float = 3300.
    cover_u: float = 0.15
    side_u: float = 0.10
    bottom_u: float = 0.10
    air_c: float = 10.
    soil_c: float = 10.
    conductivity_w_mk: float = 0.60
    max_step_minutes: float = 5.

    def validate(self):
        for name, value in asdict(self).items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
        if not isinstance(self.layers, int) or not 2 <= self.layers <= 80:
            raise ValueError("Use 2–80 integer layers.")
        for name in ('initial_bottom_c','initial_top_c','source_c','return_c','minimum_delivery_c'):
            if not 5 <= getattr(self, name) <= 95:
                raise ValueError(f"{name} must be between 5 and 95 °C for this liquid-water model.")
        if not -40 <= self.air_c <= 60 or not 5 <= self.soil_c <= 60:
            raise ValueError("Boundary temperatures outside the supported range.")
        if self.initial_top_c < self.initial_bottom_c:
            raise ValueError("Initial top temperature must not be below the bottom temperature.")
        if self.source_c <= self.return_c or self.minimum_delivery_c <= self.return_c:
            raise ValueError("Source and minimum delivery temperatures must exceed return temperature.")
        if self.source_c < self.initial_top_c:
            raise ValueError("Initial top temperature must not exceed source temperature.")
        for name in ('cover_u','side_u','bottom_u','conductivity_w_mk','max_charge_kw','max_discharge_kw'):
            if getattr(self,name) < 0:
                raise ValueError(f"{name} must be nonnegative.")
        if self.max_flow_m3_h <= 0 or not 0 < self.max_step_minutes <= 15:
            raise ValueError("Positive flow limit and a time step up to 15 minutes are required.")


def layers_from_geometry(g, count):
    """Equal-height layers, unequal volumes; z measured upward from pit bottom."""
    l,b,s,h = (g[k] for k in ('l','b','s','h'))
    if not all(math.isfinite(x) for x in (l,b,s,h)) or min(l,b,h) <= 0 or s < 0:
        raise ValueError("Invalid water geometry.")
    dz = h/count
    def volume(z):
        return l*b*z+s*(l+b)*z*z+4*s*s*z**3/3
    nodes=[]
    for i in range(count):
        z0,z1=i*dz,(i+1)*dz
        l0,l1,b0,b1=l+2*s*z0,l+2*s*z1,b+2*s*z0,b+2*s*z1
        nodes.append(dict(layer=i+1, z_bottom_m=z0, z_top_m=z1,
                          volume_m3=volume(z1)-volume(z0),
                          side_area_m2=(l0+l1+b0+b1)*dz*math.sqrt(1+s*s),
                          top_area_m2=l1*b1))
    return nodes


def mix_inversions(temperatures, capacities):
    """Pool adjacent buoyantly unstable layers, conserving their sensible heat."""
    blocks=[]
    for i,(t,c) in enumerate(zip(temperatures,capacities)):
        blocks.append([i,i,c,c*t])
        while len(blocks)>1 and blocks[-2][3]/blocks[-2][2] > blocks[-1][3]/blocks[-1][2]:
            right=blocks.pop(); left=blocks.pop()
            blocks.append([left[0],right[1],left[2]+right[2],left[3]+right[3]])
    result=list(temperatures)
    for first,last,c,e in blocks:
        if first != last:
            result[first:last+1]=[e/c]*(last-first+1)
    return result


def simulate(g, settings, profile):
    """profile: hourly (net surplus kW, requested storage discharge kW).

    Simultaneous requests are rejected: network bypass must be settled upstream.
    Returned row 0 is initial state; row n is end of input interval n.
    Boundary losses are signed positive out of storage, negative for heat gains.
    """
    settings.validate()
    cfg=settings
    profile=list(profile)
    if not 1 <= len(profile) <= 8784:
        raise ValueError("Supply 1–8784 consecutive hourly records.")
    for charge,discharge in profile:
        if not all(math.isfinite(v) and v>=0 for v in (charge,discharge)):
            raise ValueError("Hourly powers must be finite and nonnegative.")
        if charge>0 and discharge>0:
            raise ValueError("Resolve direct-network bypass first: do not request charge and discharge in the same hour.")
    nodes=layers_from_geometry(g,cfg.layers)
    volumes=[r['volume_m3'] for r in nodes]
    capacities=[CV*v for v in volumes]
    n=cfg.layers; dz=g['h']/n
    # Midpoint sampling of the user-defined initial vertical temperature profile.
    t=[cfg.initial_bottom_c+(cfg.initial_top_c-cfg.initial_bottom_c)*(i+.5)/n for i in range(n)]
    conduct=[cfg.conductivity_w_mk*nodes[i]['top_area_m2']/dz/1000 for i in range(n-1)]
    wall=[cfg.side_u*r['side_area_m2']/1000 for r in nodes]
    cover=cfg.cover_u*nodes[-1]['top_area_m2']/1000
    bottom=cfg.bottom_u*g['l']*g['b']/1000
    energy=lambda ts: sum(c*v for c,v in zip(capacities,ts))
    initial_energy=energy(t)
    total=dict(charge_kwh=0.,discharge_kwh=0.,cover_loss_kwh=0.,side_loss_kwh=0.,bottom_loss_kwh=0.)
    history=[]
    def snapshot(hour,interval):
        e=energy(t)
        residual=e-initial_energy-total['charge_kwh']+total['discharge_kwh']+sum(total[k] for k in ('cover_loss_kwh','side_loss_kwh','bottom_loss_kwh'))
        history.append(dict(hour=hour, top_c=t[-1],bottom_c=t[0],mean_c=e/sum(capacities),
                            energy_above_return_mwh=sum(c*max(0,v-cfg.return_c) for c,v in zip(capacities,t))/1000,
                            balance_residual_kwh=residual,temperatures_c=t[:],**interval))
    empty=dict(charge_mwh=0.,discharge_mwh=0.,cover_loss_mwh=0.,side_loss_mwh=0.,bottom_loss_mwh=0.,
               unaccepted_surplus_mwh=0.,unserved_request_mwh=0.,charge_flow_m3_h=0.,discharge_flow_m3_h=0.)
    snapshot(0,empty)
    steps=0
    for hour,(requested_in,requested_out) in enumerate(profile,1):
        elapsed=0.; inc={k:0. for k in total}; flow_in=flow_out=0.
        while elapsed < 1-1e-12:
            cflow=dflow=0.
            if requested_in>0 and cfg.source_c>t[-1] and cfg.source_c-t[0]>1e-9:
                cflow=min(cfg.max_flow_m3_h,min(requested_in,cfg.max_charge_kw)/(CV*(cfg.source_c-t[0])))
            if requested_out>0 and t[-1]>=cfg.minimum_delivery_c and t[-1]-cfg.return_c>1e-9:
                dflow=min(cfg.max_flow_m3_h,min(requested_out,cfg.max_discharge_kw)/(CV*(t[-1]-cfg.return_c)))
            flow=cflow+dflow
            # Explicit monotone update: outgoing coefficients consume <=20% capacity.
            rates=[CV*flow+wall[i]+(cover if i==n-1 else 0)+(bottom if i==0 else 0)
                   +(conduct[i-1] if i else 0)+(conduct[i] if i<n-1 else 0) for i in range(n)]
            stable=min((.2*capacities[i]/r for i,r in enumerate(rates) if r>0),default=1.)
            dt=min(1-elapsed,cfg.max_step_minutes/60,stable)
            steps+=1
            if steps>2000000 or dt<1e-9:
                raise ValueError("Inputs require too many time steps; review flow, geometry and heat-transfer coefficients.")
            delta=[-wall[i]*(t[i]-cfg.soil_c) for i in range(n)]
            cover_q=cover*(t[-1]-cfg.air_c); bottom_q=bottom*(t[0]-cfg.soil_c)
            delta[-1]-=cover_q;delta[0]-=bottom_q
            for i,k in enumerate(conduct):
                q=k*(t[i+1]-t[i]);delta[i]+=q;delta[i+1]-=q
            for i in range(n):
                if cflow:
                    delta[i]+=CV*cflow*((cfg.source_c if i==n-1 else t[i+1])-t[i])
                if dflow:
                    delta[i]+=CV*dflow*((cfg.return_c if i==0 else t[i-1])-t[i])
            increment=dict(charge_kwh=CV*cflow*(cfg.source_c-t[0])*dt,
                           discharge_kwh=CV*dflow*(t[-1]-cfg.return_c)*dt,
                           cover_loss_kwh=cover_q*dt,side_loss_kwh=sum(w*(v-cfg.soil_c) for w,v in zip(wall,t))*dt,
                           bottom_loss_kwh=bottom_q*dt)
            for key,value in increment.items():
                total[key]+=value;inc[key]+=value
            t=mix_inversions([v+dt*d/c for v,d,c in zip(t,delta,capacities)],capacities)
            if min(t)<5 or max(t)>95:
                raise ValueError("Water left the 5–95 °C liquid-model range; freezing/boiling is not modelled.")
            elapsed+=dt;flow_in+=cflow*dt;flow_out+=dflow*dt
        interval={k.replace('_kwh','_mwh'):v/1000 for k,v in inc.items()}
        interval.update(unaccepted_surplus_mwh=max(0,requested_in-inc['charge_kwh'])/1000,
                        unserved_request_mwh=max(0,requested_out-inc['discharge_kwh'])/1000,
                        charge_flow_m3_h=flow_in,discharge_flow_m3_h=flow_out)
        snapshot(hour,interval)
    return dict(settings=asdict(cfg),geometry=g,layers=nodes,history=history,profile=profile,
                totals={k.replace('_kwh','_mwh'):v/1000 for k,v in total.items()},
                substeps=steps, status='Preliminary uncalibrated finite-volume screening model')
