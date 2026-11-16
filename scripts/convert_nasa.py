"""NASA PCoE 배터리 열화 데이터(B0005 · B0006 · B0007 · B0018) .mat → 수업용 CSV.

사용: python -I convert_nasa.py <mat 폴더> <출력 public 폴더> <출력 private 폴더>

만드는 파일
  public/cycles_summary.csv      방전 1회 = 1줄 (B0005 · B0006 · B0007)
  public/discharge_curves.csv    방전 중 시간 · 전압 · 전류 · 온도 (B0005 · B0006 · B0007)
  public/hidden_B0018_input.csv  B0018의 충전 · 사이클 · 내부 저항 입력(방전 관련 열 제외)
  private/hidden_B0018_answer.csv B0018 정답(용량 · SOH)  ← 공개 저장소에 올리지 않음
"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

RATED_AH = 2.0          # 정격 용량 (README: 2Ahr → 1.4Ahr가 EOL)
CELLS = ["B0005", "B0006", "B0007", "B0018"]
HIDDEN = "B0018"


def scalar(x):
    """MATLAB 스칼라(복소수 포함) → float. 없으면 NaN."""
    try:
        v = np.atleast_1d(x).ravel()
        if v.size == 0:
            return np.nan
        v = v[0]
        if np.iscomplexobj(v):
            v = v.real
        return float(v)
    except Exception:
        return np.nan


def mat_date(t):
    t = np.atleast_1d(t).ravel()
    return datetime(int(t[0]), int(t[1]), int(t[2]), int(t[3]), int(t[4]), int(t[5]))


def load_cell(path: Path):
    m = loadmat(path, squeeze_me=True, struct_as_record=False)
    key = [k for k in m if not k.startswith("__")][0]
    return key, list(m[key].cycle)


def convert_cell(cell_id, cycles):
    rows, curves = [], []
    last_charge = None
    last_imp = None
    n = 0
    for c in cycles:
        if c.type == "charge":
            last_charge = c
        elif c.type == "impedance":
            last_imp = c
        elif c.type == "discharge":
            d = c.data
            t = np.atleast_1d(d.Time).astype(float)
            v = np.atleast_1d(d.Voltage_measured).astype(float)
            i = np.atleast_1d(d.Current_measured).astype(float)
            temp = np.atleast_1d(d.Temperature_measured).astype(float)
            cap = scalar(d.Capacity)
            if t.size < 5 or not np.isfinite(cap):
                continue  # 측정이 끊긴 사이클은 뺀다
            n += 1
            row = {
                "cell_id": cell_id,
                "cycle": n,
                "date": mat_date(c.time).strftime("%Y-%m-%d %H:%M"),
                "ambient_temp": scalar(c.ambient_temperature),
                "capacity_Ah": round(cap, 4),
                "soh_pct": round(cap / RATED_AH * 100, 2),
                "discharge_time_s": round(float(t[-1]), 1),
                "min_voltage": round(float(np.nanmin(v)), 4),
                "mean_voltage": round(float(np.nanmean(v)), 4),
                "start_temp": round(float(temp[0]), 2),
                "max_temp": round(float(np.nanmax(temp)), 2),
                "temp_rise": round(float(np.nanmax(temp) - temp[0]), 2),
            }
            if last_charge is not None:
                cd = last_charge.data
                ct = np.atleast_1d(cd.Time).astype(float)
                ctemp = np.atleast_1d(cd.Temperature_measured).astype(float)
                ci = np.atleast_1d(cd.Current_measured).astype(float)
                row["charge_time_s"] = round(float(ct[-1]), 1)
                row["charge_max_temp"] = round(float(np.nanmax(ctemp)), 2)
                # 정전류(CC) 구간: 전류가 1.4A 넘는 동안
                cc = ct[ci > 1.4]
                row["cc_charge_time_s"] = round(float(cc[-1] - cc[0]), 1) if cc.size > 1 else np.nan
            else:
                row["charge_time_s"] = np.nan
                row["charge_max_temp"] = np.nan
                row["cc_charge_time_s"] = np.nan
            if last_imp is not None:
                row["re_ohm"] = round(scalar(last_imp.data.Re), 5)
                row["rct_ohm"] = round(scalar(last_imp.data.Rct), 5)
            else:
                row["re_ohm"] = np.nan
                row["rct_ohm"] = np.nan
            rows.append(row)
            curves.append(pd.DataFrame({
                "cell_id": cell_id,
                "cycle": n,
                "t_s": np.round(t, 1),
                "voltage": np.round(v, 4),
                "current": np.round(i, 4),
                "temp": np.round(temp, 2),
            }))
    return pd.DataFrame(rows), pd.concat(curves, ignore_index=True)


def main(mat_dir, pub_dir, priv_dir):
    mat_dir, pub_dir, priv_dir = Path(mat_dir), Path(pub_dir), Path(priv_dir)
    pub_dir.mkdir(parents=True, exist_ok=True)
    priv_dir.mkdir(parents=True, exist_ok=True)
    summaries, curves = [], []
    for cell in CELLS:
        key, cycles = load_cell(mat_dir / f"{cell}.mat")
        s, cv = convert_cell(key, cycles)
        print(f"{cell}: 방전 {len(s)}회 · 곡선 {len(cv)}점 · 용량 {s.capacity_Ah.iloc[0]:.3f} → {s.capacity_Ah.iloc[-1]:.3f} Ah")
        summaries.append(s)
        curves.append(cv)
    summary = pd.concat(summaries, ignore_index=True)
    curve = pd.concat(curves, ignore_index=True)

    vis = summary[summary.cell_id != HIDDEN]
    vis.to_csv(pub_dir / "cycles_summary.csv", index=False)
    curve[curve.cell_id != HIDDEN].to_csv(pub_dir / "discharge_curves.csv", index=False)

    hid = summary[summary.cell_id == HIDDEN]
    # 방전 시간 · 전압 · 온도는 용량을 거의 그대로 드러내므로(2A 정전류) 입력에서 뺀다.
    # 대회 과제 = "충전 데이터 · 사이클 · 내부 저항만으로 용량 맞히기"
    hidden_input_cols = ["cell_id", "cycle", "date", "ambient_temp", "start_temp",
                         "charge_time_s", "charge_max_temp", "cc_charge_time_s", "re_ohm", "rct_ohm"]
    hid[hidden_input_cols].to_csv(pub_dir / "hidden_B0018_input.csv", index=False)
    hid[["cell_id", "cycle", "capacity_Ah", "soh_pct"]].to_csv(priv_dir / "hidden_B0018_answer.csv", index=False)
    curve[curve.cell_id == HIDDEN].to_csv(priv_dir / "hidden_B0018_curves.csv", index=False)

    print("\n80% 도달 사이클(capacity ≤ 1.6Ah 첫 사이클)")
    for cell, g in summary.groupby("cell_id"):
        hit = g[g.capacity_Ah <= 0.8 * RATED_AH]
        print(f"  {cell}: {int(hit.cycle.iloc[0]) if len(hit) else '도달 안 함'} / 총 {len(g)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
