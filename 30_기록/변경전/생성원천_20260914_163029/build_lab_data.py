"""Create explicitly synthetic teaching inputs and a configurable original-data manifest."""
from pathlib import Path
import csv
import json
import copy
import random

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "10_실습/완성본/equipment-assistant"


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def column(number, name, meaning, unit="미확인", kind="number", origin="패키지 R5; 원문 가이드북 재대조 필요"):
    return {"id": number, "name": name, "meaning": meaning, "unit": unit, "type": kind,
            "meaning_status": "documented" if unit != "미확인" else "needs_verification", "source": origin}


def main():
    columns = [
        column(1,"No_Shot","LOT 내부 샷 번호","샷"),
        column(2,"Machine_Cycle_Time","기계 사이클 시간","s"),
        column(3,"Cycle_Time","이전 샷과 현재 샷 사이 간격","s"),
        *[column(3+i,f"Barrel_Temp_Z{i}",f"배럴 {i}구역 온도","°C") for i in range(1,5)],
        column(8,"Hopper_Temp","호퍼 온도","°C"),
        column(9,"Injection_Pressure_Real_Time","사출 시간; 이름의 Pressure만 보고 압력으로 해석하지 않음","s"),
        column(10,"Screw_Position","스크류 최소 위치","mm"),
        column(11,"Injection_Peak_Press","최대 사출 압력"),
        column(12,"Max_Injection_Rate","최대 사출률"),
        column(13,"Screw_Velocity","스크류 속도"),
        column(14,"VP_Time","충진 시간","s"),
        column(15,"VP_Position","보압 절환 위치","mm"),
        column(16,"Weighing_Start_Position","보압 종료 위치","mm"),
        column(17,"VP_Press","사출에서 보압으로 전환할 때 압력"),
        column(18,"Plasticizing_Time","계량 시간","s"),
        column(19,"Plasticizing_Start_Position","계량 시작 위치","mm"),
        column(20,"Plasticizing_End_Position","계량 종료 위치","mm"),
        column(21,"Plasticizing_RPM","계량 스크류 회전수","rpm"),
        column(22,"Minimum_Cushion","쿠션 최소 위치","mm"),
        column(23,"Cooling_Time","냉각 시간","s"),
        column(24,"Back_Flow","배압; 역류량으로 해석하지 않음"),
        column(25,"Decompression_Time","석백 시간","s"),
        column(26,"_ID","파일의 순서 식별자","순서")]
    # This is a new designed series. No factory event, measured defect or original row is reproduced.
    randomizer = random.Random(20260914)
    rows, settings_rows, log_rows = [], [], []
    for lot in range(6):
        for shot in range(240):
            cushion = 8 + lot * .2 + randomizer.gauss(0, .12)
            if lot == 4 and 110 <= shot < 125:
                cushion += 2.5
            if lot == 5:
                cushion -= max(0, shot - 60) * .007
            row = {entry["name"]: round(10 + randomizer.gauss(0, .2), 4) for entry in columns}
            row.update(No_Shot=shot, _ID=lot*240+shot, Minimum_Cushion=round(cushion,4),
                       Screw_Position=round(cushion,4), Injection_Pressure_Real_Time=1.2,
                       Machine_Cycle_Time=30, Cycle_Time=30, Plasticizing_Time=4,
                       Barrel_Temp_Z1=200, Barrel_Temp_Z2=205, Barrel_Temp_Z3=210, Barrel_Temp_Z4=215,
                       Hopper_Temp=50, Cooling_Time=15)
            rows.append(row)
        settings_rows.append({"lot": str(lot), "cushion_reference": 8+lot*.2,
                              "setting_status": "설계: 기준값", "revision": "B"})
        log_rows.append({"lot": str(lot), "shot_count":240,"inspection_status":"미검사",
                         "note":"교육용 합성. 품질과 원인을 확인한 기록이 아님"})
    write_csv(APP/"data/generated/shots.csv", [entry["name"] for entry in columns], rows)
    write_csv(APP/"data/generated/conditions.csv", list(settings_rows[0]), settings_rows)
    write_csv(APP/"data/generated/worklog.csv", list(log_rows[0]), log_rows)
    condition_columns = [column(101,"lot","이 원천의 LOT 식별자","ID","text","설계"),
                         column(102,"cushion_reference","교육용 설정 기준","mm",origin="설계"),
                         column(103,"setting_status","기록의 성격","상태","text","설계"),
                         column(104,"revision","개정 번호","ID","text","설계")]
    log_columns = [column(201,"lot","이 원천의 LOT 식별자","ID","text","설계"),
                   column(202,"shot_count","LOT에 포함된 샷 수","샷",origin="설계"),
                   column(203,"inspection_status","검사 여부","상태","text","설계"),
                   column(204,"note","기록 설명","문장","text","설계")]
    synthetic = {
        "shots":{"path":"data/generated/shots.csv","table":"synthetic_shots","columns":columns,
                 "shot_column":"No_Shot","order_column":"_ID","time_column":None,
                 "lot_rule":"파일 첫 묶음 0, No_Shot이 0으로 돌아오면 다음 LOT. 첫 행이 LOT 중간이면 부분 LOT",
                 "provenance":"교육용 합성: 새로 생성한 순차 자료. KAMP 실측이 아님"},
        "conditions":{"path":"data/generated/conditions.csv","table":"synthetic_conditions","columns":condition_columns,
                      "lot_column":"lot","provenance":"설계: 교육용 합성 샷과 연결한 설정표"},
        "worklog":{"path":"data/generated/worklog.csv","table":"synthetic_worklog","columns":log_columns,
                   "lot_column":"lot","provenance":"설계: 교육용 합성 샷 수를 집계한 작업 기록"}}
    labeled = []
    for index in range(360):
        value = randomizer.gauss(8, .8)
        bad = int(value > 9 or value < 6.5)
        labeled.append({"sequence":index,"cushion":round(value,4),"cycle":round(randomizer.gauss(30,1),3),
                        "label":bad,"label_origin":"교육용 합성 규칙 라벨. 실물 불량 라벨 아님"})
    write_csv(APP/"data/generated/labeled.csv",list(labeled[0]),labeled)
    synthetic["labeled"]={"path":"data/generated/labeled.csv","table":"synthetic_labeled",
        "columns":[column(301,"sequence","샘플 순서","순서",origin="합성"),
                   column(302,"cushion","쿠션 관측값","mm",origin="합성"),
                   column(303,"cycle","사이클 시간","s",origin="합성"),
                   column(304,"label","합성 규칙 판정","0=기준 안/1=기준 밖",origin="합성"),
                   column(305,"label_origin","라벨 생성 방식","설명","text","합성")],
        "order_column":"sequence","label_column_id":304,"label_values":{"0":0,"1":1},
        "provenance":"교육용 합성: 규칙 라벨 재현 실습이며 품질 예측 실증 아님"}
    original={"shots":{**copy.deepcopy(synthetic["shots"]),"path":"data/raw/InjectionMolding_Raw_Data.csv","table":"kamp_shots",
                       "provenance":"KAMP 사출성형 예지보전(2022); 원본 경로·이용조건 확인 후 사용"}}
    for entry in synthetic["shots"]["columns"]:
        entry["source"] += "; 합성 프로필의 값은 생성값"
    profiles={"synthetic":{"label":"교육용 합성","sources":synthetic,"ontology":"ontology/synthetic.csv","documents":[]},
              "kamp":{"label":"KAMP 원본 연결","sources":original,"ontology":"ontology/kamp.csv","documents":[]}}
    mapping={"version":1,"profiles":profiles,
             "vision":{"path":"data/raw/thermal","manifest":"data/raw/thermal/manifest.csv",
                       "shape":[256,320],"unit":"°C","provenance":"KAMP 원본 수령 후 변환. 기본 이미지 자동 대체 없음"},
             "rul":{"path":"data/raw/CMAPSS","provenance":"NASA C-MAPSS 공개 대체 자료; 사출 설비 실증 아님"}}
    (APP/"mapping.json").write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding="utf-8")
    relations=[]
    for lot in range(6):
        relations += [{"source":f"synthetic:shots:lot:{lot}","source_type":"lot","relation":"has_conditions",
                       "target":f"synthetic:conditions:lot:{lot}","target_type":"condition_record","provenance":"설계: 생성 LOT 키 연결"},
                      {"source":f"synthetic:shots:lot:{lot}","source_type":"lot","relation":"has_log",
                       "target":f"synthetic:worklog:lot:{lot}","target_type":"worklog","provenance":"설계: 생성 LOT 키 연결"}]
    relations += [{"source":"synthetic:channel:22","source_type":"channel","relation":"observes",
                   "target":"synthetic:component:screw","target_type":"component",
                   "provenance":"관계 설계; 패키지 AAS의 쿠션-스크류 대응 참고, 원인 확정 아님"}]
    write_csv(APP/"ontology/synthetic.csv",list(relations[0]),relations)
    (APP/"ontology/kamp.csv").write_text("source,source_type,relation,target,target_type,provenance\n",encoding="utf-8")
    print("합성 표 4개와 원천 매핑을 생성했습니다. 원시 실데이터를 복사하거나 실측하지 않았습니다.")


if __name__ == "__main__":
    main()
