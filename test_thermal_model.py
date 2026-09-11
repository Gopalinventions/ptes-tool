import math
import unittest
from dataclasses import replace
from designer_integration import design_geometry
from thermal_model import CV, Settings, layers_from_geometry, mix_inversions, simulate


class ThermalTests(unittest.TestCase):
    def setUp(self):
        self.g=design_geometry(125000,15,1.5,2.5,1.16)[1]
        self.adiabatic=Settings(cover_u=0,side_u=0,bottom_u=0,conductivity_w_mk=0)

    def test_geometry(self):
        nodes=layers_from_geometry(self.g,20)
        self.assertAlmostEqual(sum(n['volume_m3'] for n in nodes),125000)
        expected=(self.g['l']+self.g['wl']+self.g['b']+self.g['wb'])*self.g['h']*math.sqrt(1+self.g['s']**2)
        self.assertAlmostEqual(sum(n['side_area_m2'] for n in nodes),expected)
        self.assertGreater(nodes[-1]['volume_m3'],nodes[0]['volume_m3'])

    def test_adiabatic_idle(self):
        result=simulate(self.g,replace(self.adiabatic,initial_top_c=85),[(0,0)]*24)
        self.assertEqual(result['history'][0]['temperatures_c'],result['history'][-1]['temperatures_c'])

    def test_charge_and_balance(self):
        result=simulate(self.g,self.adiabatic,[(3300,0)]*48)
        last=result['history'][-1]
        self.assertGreater(last['top_c'],last['bottom_c'])
        self.assertAlmostEqual(result['totals']['charge_mwh'],158.4,places=7)
        self.assertLess(max(abs(r['balance_residual_kwh']) for r in result['history']),1e-6)
        self.assertLessEqual(last['top_c'],90)

    def test_discharge_cutoff(self):
        cold=simulate(self.g,self.adiabatic,[(0,3300)]*4)
        self.assertEqual(cold['totals']['discharge_mwh'],0)
        hot=simulate(self.g,replace(self.adiabatic,initial_top_c=85,initial_bottom_c=85),[(0,3300)]*24)
        self.assertAlmostEqual(hot['totals']['discharge_mwh'],79.2,places=7)
        self.assertLess(hot['history'][-1]['bottom_c'],hot['history'][-1]['top_c'])

    def test_mixing_conserves_energy(self):
        temps=[80,50,60,40,90]; caps=[1,2,3,4,5]
        mixed=mix_inversions(temps,caps)
        self.assertEqual(mixed,sorted(mixed))
        self.assertAlmostEqual(sum(t*c for t,c in zip(temps,caps)),sum(t*c for t,c in zip(mixed,caps)))

    def test_loss_and_conduction_balance(self):
        result=simulate(self.g,Settings(initial_top_c=85),[(0,0)]*48)
        self.assertGreater(result['totals']['cover_loss_mwh'],0)
        self.assertGreater(result['totals']['side_loss_mwh'],0)
        self.assertGreater(result['totals']['bottom_loss_mwh'],0)
        self.assertLess(max(abs(r['balance_residual_kwh']) for r in result['history']),1e-6)

    def test_cooling_analytical_and_timestep(self):
        g=design_geometry(1000,10,0,0,1)[1]
        cfg=replace(self.adiabatic,side_u=1,initial_top_c=80,initial_bottom_c=80)
        expected=10+70*math.exp(-.4*24/(CV*1000))
        coarse=simulate(g,cfg,[(0,0)]*24)['history'][-1]['mean_c']
        fine=simulate(g,replace(cfg,max_step_minutes=1),[(0,0)]*24)['history'][-1]['mean_c']
        self.assertLess(abs(coarse-expected),.001)
        self.assertLess(abs(fine-expected),abs(coarse-expected))

    def test_invalid(self):
        for profile in [[],[(1,1)],[(float('nan'),0)],[(-1,0)]]:
            with self.assertRaises(ValueError):simulate(self.g,self.adiabatic,profile)
        with self.assertRaises(ValueError):simulate(self.g,replace(self.adiabatic,return_c=90),[(0,0)])


if __name__=='__main__': unittest.main()
