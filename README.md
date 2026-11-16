# battery-ml-data — 「내 배터리는 몇 살인가」 실습 데이터

이차전지 학과 파이썬 · 머신러닝 · 딥러닝 특강(AICEC 인공지능융합교육원)에서 쓰는 리튬이온 배터리 열화 데이터입니다.
Colab에서 아래 한 셀로 바로 읽습니다. 다운로드할 것이 없습니다.

```python
import pandas as pd
BASE = "https://raw.githubusercontent.com/aicec/battery-ml-data/main/"
summary = pd.read_csv(BASE + "cycles_summary.csv")      # 방전 1회 = 1줄
curves  = pd.read_csv(BASE + "discharge_curves.csv")    # 방전 중 전압 · 전류 · 온도
summary.head()
```

## 원본
NASA Ames Prognostics Center of Excellence(PCoE) **Battery Data Set** — 셀 B0005 · B0006 · B0007 · B0018.
18650 리튬이온 셀을 상온(24℃)에서 1.5A 정전류 → 4.2V 정전압으로 충전하고 2A 정전류로 방전(차단 전압 2.7 · 2.5 · 2.2 · 2.5V)하며 노화시킨 실험입니다. 정격 용량 2.0Ah, 1.4Ah(70%)에서 실험 종료.
원본은 MATLAB(.mat) 형식이며 `scripts/convert_nasa.py`로 CSV로 바꿨습니다. 원본 데이터의 저작권과 이용 조건은 NASA PCoE 데이터 저장소 안내를 따릅니다.

## cycles_summary.csv — 방전 1회 = 1줄 (504행 · B0005 · B0006 · B0007 각 168회)
| 열 | 뜻 |
|---|---|
| cell_id | 셀 이름 |
| cycle | 방전 회차(1부터) |
| date | 방전 시작 시각 |
| ambient_temp | 주변 온도(℃) |
| **capacity_Ah** | 방전 용량(Ah) — 이 수업의 예측 대상 |
| soh_pct | 용량 ÷ 2.0Ah × 100 (배터리 건강 상태 %) |
| discharge_time_s | 방전에 걸린 시간(초) |
| min_voltage · mean_voltage | 방전 중 최저 · 평균 단자 전압(V) |
| start_temp · max_temp · temp_rise | 방전 시작 · 최고 셀 온도 · 상승폭(℃) |
| charge_time_s | 직전 충전 전체 시간(초) |
| charge_max_temp | 직전 충전 중 최고 셀 온도(℃) |
| cc_charge_time_s | 직전 충전의 정전류 구간 길이(초, 전류 > 1.4A) |
| re_ohm · rct_ohm | 직전 임피던스 측정의 전해질 저항 · 전하 전달 저항(Ω). 첫 측정 전 사이클은 비어 있음 |

## discharge_curves.csv — 방전 중 측정값 (150,855행 · 약 9초 간격)
| 열 | 뜻 |
|---|---|
| cell_id · cycle | 요약표와 같은 키 |
| t_s | 방전 시작 후 시간(초) |
| voltage | 단자 전압(V) |
| current | 전류(A, 방전은 음수) |
| temp | 셀 온도(℃) |

## hidden_B0018_input.csv — 마지막 날 「숨긴 셀」 입력 (132행)
B0018의 충전 · 사이클 · 내부 저항 열만 있고 **용량과 방전 관련 열은 없습니다.**
과제: 이 입력만으로 각 회차의 용량(capacity_Ah)을 예측해 제출합니다. 정답은 수업에서 공개합니다.

## 알아 두면 좋은 특징
- 용량은 대체로 줄지만 가끔 **거꾸로 오르는 회차**가 있습니다(쉬었다가 다시 방전하면 일부 회복).
- 2A 정전류 방전이라 **방전 시간은 용량과 거의 같은 정보**입니다. 예측 특성으로 쓸 때 무엇을 예측하는지 생각해 보세요.
- 내부 저항(re_ohm · rct_ohm)은 노화할수록 오르고, 용량과는 반대로 움직입니다.
