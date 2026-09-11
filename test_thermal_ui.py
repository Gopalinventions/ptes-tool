"""Adapter smoke tests with a Streamlit stub; not a live app test."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch
import pandas as pd
from designer_integration import design_geometry


class Stub(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit');self.session_state={};self.messages=[];self.errors=[];self.run=True
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def __getattr__(self,name):
        if name in ('expander','spinner'):return lambda *a,**k:self
        if name=='columns':return lambda n:[self]*n
        if name=='number_input':return lambda label,*a,**k: (1 if k.get('key') in ('th_cd','th_id','th_dd') else k.get('value',a[2] if len(a)>2 else 0))
        if name=='selectbox':return lambda label,options,**k:options[k.get('index',0)]
        if name=='radio':return lambda label,options,**k:options[0]
        if name=='checkbox':return lambda label,**k:k.get('value',False)
        if name=='button':return lambda *a,**k:self.run
        if name=='error':return lambda text:self.errors.append(text)
        return lambda *a,**k:self.messages.append((name,a))


class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub=Stub();components=types.ModuleType('streamlit.components');v1=types.ModuleType('streamlit.components.v1');v1.html=lambda *a,**k:None
        components.v1=v1;cls.stub.components=components
        with patch.dict(sys.modules,{'streamlit':cls.stub,'streamlit.components':components,'streamlit.components.v1':v1}):
            cls.ui=importlib.import_module('thermal_ui')

    def test_run_and_stale_state(self):
        g=design_geometry(125000,15,1.5,2.5,1.16)[1]
        self.ui.render_thermal(g,3300,30)
        self.assertFalse(self.stub.errors)
        self.assertIn('thermal_run',self.stub.session_state)
        result=self.stub.session_state['thermal_run'][1]
        self.assertIn('refinement',result)
        self.assertEqual(len(result['history']),73)
        self.stub.run=False
        self.ui.render_thermal(design_geometry(100000,15,1.5,2.5,1.16)[1],3300,30)
        self.assertTrue(any('Inputs changed' in str(args) for name,args in self.stub.messages))

    def test_hourly_validation(self):
        frame=pd.DataFrame({'timestamp':['2025-05-01T00:00:00Z','2025-05-01T01:00:00Z'],'net_charge_kw':[10,0],'discharge_request_kw':[0,10]})
        profile,times=self.ui.read_profile(frame)
        self.assertEqual(profile,[(10,0),(0,10)])
        frame.loc[1,'timestamp']=frame.loc[0,'timestamp']
        with self.assertRaises(ValueError):self.ui.read_profile(frame)


if __name__=='__main__':unittest.main()
