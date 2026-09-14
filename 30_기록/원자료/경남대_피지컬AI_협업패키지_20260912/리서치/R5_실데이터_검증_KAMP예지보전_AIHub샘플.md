# R5 · 실데이터 검증 (2026-09-10) — 받은 파일을 직접 열어 확인한 것

## 1. KAMP 「사출성형 예지보전 AI 데이터셋」 (2022-12-23 등록, 2025-04-02 갱신, ㈜인터엑스/네스트필드, 사용조건 「콘텐츠 변경허용」, 출처 표기 의무)
**우리가 앞서 근거로 쓴 2020 「사출성형기 AI 데이터셋」(UNIST 가이드북)과 다른 데이터셋이다.** KAMP 네비게이터(사출성형 × 품질보증·예지보전)에 이것 하나만 나왔다. 2020 것이 목록에 남아 있는지는 미확인.

### 파일
- `data/InjectionMolding_Raw_Data.csv` 1,030,635행 × 26열, 136MB. 결측 0, 중복 0, `_ID` 유일.
- `AASX 및 변환파일/` — `Injection_Molding_Machine_AAS_Final.aasx`·`.xml`, `engineering.csv`(AAS 태그 231개), `nodeset.xml`(OPC UA), `syscfg.json`. **IEC 63278-1 AAS 자산 모델 실물.**

### 현장 (가이드북 원문)
- 제조 분야 소형 사출품, 수집 2021-01-01~05-31(약 5개월), 분당 평균 2~3 shot, shot 단위 공정 조건 데이터. PLC/OPC UA → Edge GW → AAS 서버 → TSDB(Influx) → CSV.
- **페인포인트 원문**: "현재 제조현장에서 사용되고 있는 사출 성형 설비는 구식 모델이거나 제조사에 의해 외부 인터페이스가 개방되어 있지 않기 때문에 실시간 데이터 수집이 어려운 상황" / "데이터 미들웨어를 구매하여 데이터를 수집하더라도 설비 상태에 대한 레이블 정보가 없기 때문에 실제 양산이 진행되는 과정에서 설비의 상태를 확인하기는 매우 어려운 실정" / "설비의 상태 정보는 MES 등의 생산정보시스템에도 저장되어 있지 않고, 설비 관리자라 할지라도 정확하게 판단할 수 없는 부분" / 극복: "사출 공정에서는 제품뿐 아니라 설비관리 시에도 Lot 단위로 진행 → 일정 수량의 shot으로 구성된 Lot 단위 데이터의 대표값으로 설비 상태의 경향성을 판단".
- 사출 성형 단점 원문: "성형품의 품질을 빠르게 변경할 수 없다 / 성형 과정에 있어서 중간에 제어를 할 수 없다".

### 변수 26 (가이드북 표 2 원문 뜻)
No_Shot(Shot 번호, Lot 기준 카운트) · Machine_Cycle_Time · Cycle_Time(이전 shot과 현재 shot 간격) · Barrel_Temp_Z1~Z4(℃) · Hopper_Temp · Injection_Pressure_Real_Time(사출 시간, s) · Screw_Position(스크류 최소 위치) · Injection_Peak_Press · Max_Injection_Rate · Screw_Velocity · VP_Time(충진 시간) · VP_Position(보압 절환 위치) · Weighing_Start_Position(보압 끝 위치) · VP_Press(사출→보압 전환 압력) · Plasticizing_Time(계량시간) · Plasticizing_Start/End_Position · Plasticizing_Screw_Velocity(rpm; CSV 열 이름은 Plasticizing_RPM) · **Minimum_Cushion(쿠션 최소 위치)** · Cooling_Time · **Back_Flow(가이드북: 계량 중 스크류가 밀려나는 것을 저지하는 압력 = 배압)** · Decompression_Time(석백) · _ID.
- **타임스탬프 열 없음.** 순서는 `_ID`/`No_Shot`. **금형 온도·형체력 열 없음.** 0값 열 없음. 음수 소수(Screw_Position 7행·Minimum_Cushion 7행·Screw_Velocity 1행).
- **품질/설비 상태 라벨 없음.** 가이드북은 Lot(No_Shot==0 기준 407개, ≥100 shot 381개)별 대표값(평균·중앙·1/3분위)에 IQR(1.5) + DBSCAN을 적용해 **abnormal Lot 43개**를 정하고, 그 Lot의 shot에 PassOrFail=1(abnormal 9.18%)을 부여 → 오토인코더(정상만 학습, 복원오차 임계 mean+1.5σ) → k-fold 평균 정확도 0.9115·재현율 0.9059·정밀도 0.96·F1 0.9318.

### 우리가 데이터에서 직접 확인한 것
- Lot 수 407(≥100 shot 381), Lot 크기 중앙값 2,722 shot(최대 15,108).
- Lot 평균 쿠션 5.6~12.1mm로 넓게 퍼짐(제품/조건이 바뀜) — 단조 열화 추세 아님.
- **급변 실물**: lot 358(2,031 shot) 쿠션이 7.8 → 12~19mm로 중간에 튐, 계량시간 2.1 → 0.45 s. lot 357 끝부분 9.5 → 7.7. (가이드북 abnormal 목록 325~380 구간과 일치)
- **점진 실물(약함)**: lot 92(1,758 shot) 쿠션 −0.81mm 단조 감소(스피어만 −0.76). 그 외 |Δ|>1mm 점진 Lot 없음.
- → 실4(규칙 급변)는 실데이터 근거. 실5의 「서서히」는 lot 92를 실데이터 예로 쓰되 약해서 합성 구간 보강 유지(표시).

### AAS 자산 모델 (온톨로지 첫 판의 실물 근거)
계층: Injection_Molding_Machine → Identification / Component.Injection_Unit(Hopper·Band_Heater·Barrel·Cylinder·Screw(**Check_Ring**)·Nozzle) / Component.Clamping_Unit(Coolant·Mold(Cavity)·Motor_Drive) / Operational_Data(Production_Info·Defect_Info·Mold_Info.No_Shot·Status) / **Alarm_Data**(Alarm_Number·Text·Category·Raised_Time_Stamp) / **Maintenance**(Interval·Remaining_Interval·Total_Operation·Status) / **Log_Event**(Parameter_Change_Log Old/New Value·User·Machine_Mode_Change) / Energy / Controller / CAD.
26열 → AAS 경로 대응 확인(예: Minimum_Cushion → Injection_Unit.Screw.Operational_Data.Eject.Minimum_Cushion; Barrel_Temp_Z1 → Injection_Unit.Barrel.Operational_Data.Barrel_1; Cooling_Time → Clamping_Unit.Coolant). 표: `참고/AAS_사출기_자산모델_계층.csv`.
→ 실1 블록4 「공장의 지도」는 지어낸 표가 아니라 **이 자산 모델의 축소판**으로 시작한다(근거). 실4 알람은 Alarm_Data, 실8 승인·기록은 Log_Event.Parameter_Change_Log·Maintenance 슬롯에 대응(근거 있는 설계).

## 2. AI-Hub 「부품 품질 검사 영상 데이터(자동차)」 샘플(경량)
- 210장, 전부 **TL_1.도어 / 외관 손상 / 불량품**. 4224×2376 JPG. JSON(COCO 형식, BOM 있음): categories 12종(스크래치·외관 손상·고정 불량·고정핀 불량·단차·실링 불량·연계 불량·유격 불량·장착 불량·체결 불량·헤밍 불량·홀 변형), bbox 1개/장, attributes {work: 도장, part: 도어, quality: 불량품}. 라이선스 JSON: CC BY-NC(-SA 2.0).
- **샘플에는 정상(양품) 사진이 0장** → 통3(정상만 학습)에는 부족. attributes.quality 필드가 있으므로 전체 데이터에 양품이 있을 가능성. **확인 방법: 라벨링데이터 TL_1.도어.tar(57.6MB)만 받아 JSON의 quality 값을 세면 사진을 안 받고도 안다.** 부품별 라벨 tar은 전부 100MB 이하.

## 3. 결론 · 바뀌는 것
- 주 데이터 = 이 2022 예지보전 데이터셋(실물 보유·라이선스 명확·AAS 모델 동봉). 2020 데이터셋은 목록에 있으면 통2 라벨용으로 추가, 없으면 통2 「판별기」는 가이드북 방식(Lot 대표값 → 정상/비정상 라벨 → 판별)으로 = 설비 상태 판별기.
- 삽화설명서 2절(변수 26: 배럴 4존, 금형 온도 없음, 라벨 없음, 타임스탬프 없음)·4절(페인포인트에 "라벨 없음·구식 설비·MES에 상태 없음" 추가)·5절(급변 실물 lot 358, 점진 lot 92)·실1 블록4(AAS)·통2(라벨 만들기)·통5(예지보전 = 이 데이터셋의 본래 목적) 갱신.
- 남는 확인: 2020 데이터셋 존재 여부, AI-Hub 도어 라벨 tar의 양품 수.

## 4. (추가 2026-09-10) KAMP 「사출성형기 AI 데이터셋」(2020) 실물 + 「머신비전 AI 데이터셋」(6번) 실물 + AI-Hub 도어 라벨 전체
### 4-1. 사출성형기 AI 데이터셋(2020) — 받음
파일 8개: moldset_labeled/unlabeled(cn7·rg3 분리 포함), labeled_data.csv, unlabeled_data.csv, supervised_label_cn7.csv. 256MB. 라벨(PassOrFail·Reason) 실물 확인은 다음 작업에서.
### 4-2. 머신비전 AI 데이터셋(6번, 2020-12-14, 사출성형·품질보증) — 받음
- 가이드북 원문: 자동차 윈드실드 사이드 몰딩 **가스 사출**, 자동차 부품 H사. IR 카메라, 사이클 약 60초. 원본 = 성형 직후 제품의 **열화상 온도 raw(256×320)** + 파괴검사로 잰 **단면 두께(mm) 수기 라벨**. 양품 0.8mm < 두께 < 1.5mm, 그 밖은 불량. 알고리즘 비선형 SVM(좌·우 제품 각각). 데이터 1,674개·450MB(csv·json).
- 페인포인트 원문: "성형된 제품이 냉각되어 수축한 후 불량이 발생하고 이를 확인할 수 있으므로 불량 발생 시점에서 공정을 멈추거나 제어하는 것이 어렵다 … 파괴 검사를 수행하여야 하므로 모든 제품에 대해 불량 여부를 확인하기 어렵고 … 불량 판정인 경우에 앞뒤 일정 개수의 제품을 모두 재활용할 수밖에 없으므로 시간 손실이 발생한다." 가스 과다/부족 → 빈 공간 → 뒤틀림·내구성 저하(원문).
- 실물: `left_data.csv` 414행 × 81,920열(=256×320), `right_data.csv` 423행. 라벨 json 두께 값(좌 0.68~2.16, 우 0.90~2.23). 두께 규칙 적용 시 **양품 616(좌 283·우 333) / 불량 221(좌 131·우 90)**. 참고 JPG 839장(`machine_vision_image_references.zip`). 2차 가공본은 80열(특징 추출본, 414행).
- 온도 행렬을 그림으로 그리면 몰딩 두 줄이 밝게 보인다(`참고/열화상_샘플_KAMP머신비전.png`). → **통3 「사진으로 불량 판별」을 사출 자체 데이터로 한다**(정상 616장으로 학습, 불량 221장으로 확인). AI-Hub 도어 사진은 「먼저 끝났으면」 후보로 강등.
### 4-3. AI-Hub 도어 라벨 tar(TL_1.도어) 전체
JSON 13,593개, 주석 17,005개: **양품 6,058 · 불량품 10,947**, 카테고리 101/102. 전체 데이터에는 정상이 있음. 사진 원본(27.78GB)은 이제 필수 아님.
### 4-4. KAMP 50종 전수 대조 (aidataList 6쪽)
센서+품질 라벨 / 설비 예지보전 / 이미지가 **한 업종에 다 있는 곳은 사출성형뿐**(4번·56번·6번). 주조(53·54·55)·용접(5·45·51·52)·열처리(43·60·61)·소성가공(48·49)은 이미지 없음. 표면처리는 이미지(25)·예지보전(23)이 있으나 공정이 제각각. → 설비 = 사출기 **확정(데이터 근거)**.

## 5. (추가) 2020 사출성형기 데이터셋 라벨 실물 확인
- `labeled_data.csv` 7,996행(TimeStamp 열 있음), `unlabeled_data.csv` 795,315행, cn7/rg3 분리본, `supervised_label_cn7.csv` 6,736행.
- **PassOrFail 값: Y 7,925 / N 71 (불량 0.89%)** — 가이드북의 0/1 표기와 달리 실물은 Y/N.
- **Reason 값(불량 이유) 실물: 가스 35 · 초기허용불량 20 · 미성형 16** (양품은 빈칸). → "Reason 값 목록 확인 불가"였던 빈칸이 닫힘. 불량 세 종류만 있어 다중 분류보다 양품/불량 이진 + 이유 표시로 쓴다.
- 전부 0인 열 10개(Mold_Temperature 1·2·5~12) 실물 확인(가이드북과 일치; Barrel_7은 이 파일에선 0 아님 — 통계표는 moldset_labeled 기준).
