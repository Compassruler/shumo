"""Encode undefined event-conditioned metrics consistently in all CSV logs."""
import bootstrap
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main():
    changed=0
    for path in (ROOT/'data').glob('*.csv'):
        df=pd.read_csv(path,encoding='utf-8-sig')
        if not {'first_success_s','stop_s','E_aux_J'}.issubset(df.columns):continue
        masks=[(df.first_success_s<0,['first_success_energy_J','first_min_voltage_V','first_max_ice_bulk','first_dTmax_K']),
               (df.stop_s<0,['post_min_T_C','post_min_voltage_V','post_max_ice_bulk','post_energy_J'])]
        dirty=False
        for mask,cols in masks:
            cols=[c for c in cols if c in df]
            if cols and mask.any() and df.loc[mask,cols].notna().any().any():
                df.loc[mask,cols]=np.nan;dirty=True
        if dirty:
            df.to_csv(path,index=False,encoding='utf-8-sig',float_format='%.12g');changed+=1
    print('Undefined event fields normalized in',changed,'CSV files')
if __name__=='__main__':main()
