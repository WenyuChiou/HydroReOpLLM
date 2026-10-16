"""Pinned, pre-experiment inflow statistics for the deterministic benchmark.

Role: Validate the benchmark statistics and their original inflow source.

Connections and data: Called during workflow configuration checks. Reads the declared
reference window, verifies source hashes and recomputes statistics, then returns
BenchmarkBackend settings and file pins. Reference dates must precede the experiment; no
release or model call occurs here.
"""
import csv
from datetime import date,timedelta
import gzip
import hashlib
import math
from pathlib import Path

from .case import read_json
from .contracts import finite_nonnegative


def calculate_statistics(path, spec, start, end):
    """Use only the declared consecutive reference window, never future rows."""
    first,last=date.fromisoformat(start),date.fromisoformat(end)
    if first>last:
        raise ValueError("benchmark reference window is reversed")
    required={"path","sha256","date_column","flow_column","flow_to_cms","reservoir_column","reservoir_value"}
    if not isinstance(spec,dict) or set(spec)!=required:
        raise ValueError("benchmark source requires explicit columns, conversion and reservoir selection")
    scale=finite_nonnegative(spec['flow_to_cms'],'flow_to_cms')
    if not scale:
        raise ValueError("flow_to_cms must be positive")
    values={}
    opener=gzip.open if Path(path).suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle)
        columns={spec['date_column'],spec['flow_column'],spec['reservoir_column']}
        if not columns.issubset(reader.fieldnames or ()):
            raise ValueError("benchmark inflow source columns are missing")
        for row in reader:
            if row[spec['reservoir_column']]!=spec['reservoir_value']:
                continue
            day=date.fromisoformat(row[spec['date_column']])
            if not first<=day<=last:
                continue
            if day.isoformat()!=row[spec['date_column']] or day in values:
                raise ValueError("benchmark reference dates must be canonical and unique")
            values[day]=finite_nonnegative(float(row[spec['flow_column']])*scale,'reference inflow')
    expected=(last-first).days+1
    if len(values)!=expected or any(first+timedelta(days=i) not in values for i in range(expected)):
        raise ValueError("benchmark reference inflow must cover every declared day")
    monthly={str(m):[v for d,v in values.items() if d.month==m] for m in range(1,13)}
    if not all(monthly.values()):
        raise ValueError("benchmark climatology requires all twelve months")
    return {'mean_inflow_cms':math.fsum(values.values())/len(values),
            'monthly_mean_inflow_cms':{m:math.fsum(v)/len(v) for m,v in monthly.items()},
            'reference_day_count':len(values)}


def load_benchmark(spec, base, physical, simulation_start):
    """Validate source bytes, recompute statistics and reject temporal leakage."""
    allowed={'statistics','purpose','alpha'}
    if not isinstance(spec,dict) or set(spec)-allowed or not isinstance(spec.get('statistics'),str):
        raise ValueError("benchmark requires statistics, optional purpose and alpha")
    path=(Path(base)/spec['statistics']).resolve()
    data=read_json(path)
    fields={'schema_version','reservoir_id','reference_start','reference_end','source',
            'mean_inflow_cms','monthly_mean_inflow_cms','reference_day_count'}
    if set(data)!=fields or data['schema_version']!='reservoir-benchmark-statistics.v1':
        raise ValueError("unsupported benchmark statistics contract")
    if data['reservoir_id']!=physical['reservoir_id']:
        raise ValueError("benchmark statistics belong to another reservoir")
    if date.fromisoformat(data['reference_end'])>=date.fromisoformat(simulation_start):
        raise ValueError("benchmark statistics must precede the simulation start")
    source=(path.parent/data['source']['path']).resolve()
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash!=data['source']['sha256']:
        raise ValueError("benchmark reference inflow source checksum mismatch")
    actual=calculate_statistics(source,data['source'],data['reference_start'],data['reference_end'])
    declared=finite_nonnegative(data['mean_inflow_cms'],'mean_inflow_cms')
    if not math.isclose(declared,actual['mean_inflow_cms'],rel_tol=1e-12,abs_tol=1e-9):
        raise ValueError("benchmark mean does not match pinned reference inflow")
    monthly=data['monthly_mean_inflow_cms']
    if not isinstance(monthly,dict) or set(monthly)!=set(actual['monthly_mean_inflow_cms']):
        raise ValueError("benchmark needs exactly twelve monthly means")
    for m,value in actual['monthly_mean_inflow_cms'].items():
        if not math.isclose(finite_nonnegative(monthly[m],'monthly mean'),value,rel_tol=1e-12,abs_tol=1e-9):
            raise ValueError("benchmark monthly mean does not match pinned reference inflow")
    if isinstance(data['reference_day_count'],bool) or data['reference_day_count']!=actual['reference_day_count']:
        raise ValueError("benchmark reference day count mismatch")
    from .benchmark import BenchmarkBackend
    settings=dict(reservoir_id=physical['reservoir_id'],capacity_m3=physical['capacity_m3'],
                  mean_inflow_cms=actual['mean_inflow_cms'],monthly_mean_inflow_cms=actual['monthly_mean_inflow_cms'],
                  alpha=spec.get('alpha',0.85),purpose=spec.get('purpose','flood_control'),
                  source={'statistics_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'reference_start':data['reference_start'],'reference_end':data['reference_end'],
                          'reference_day_count':actual['reference_day_count'],'inflow_sha256':source_hash})
    BenchmarkBackend(**settings) # Constructor validation has no network or decision side effects.
    return settings,{str(path):hashlib.sha256(path.read_bytes()).hexdigest(),str(source):source_hash}
