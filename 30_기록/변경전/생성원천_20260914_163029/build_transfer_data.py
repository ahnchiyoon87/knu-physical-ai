"""Create an unrelated, explicitly designed library case for transfer practice."""
from pathlib import Path
import csv
import json

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"10_실습/완성본/equipment-assistant"


def main():
    folder=APP/"data/transfer"
    folder.mkdir(parents=True,exist_ok=True)
    books=[{"book_id":f"B{i:02}","category":category,"copies":copies} for i,(category,copies) in
           enumerate([("역사",3),("과학",2),("예술",4),("문학",3),("기술",2)],1)]
    loans=[{"loan_id":f"L{i:02}","book_id":f"B{(i-1)%5+1:02}","borrower_role":"학습자",
            "days_from_due":days,"state":state} for i,(days,state) in enumerate(
                [(-4,"대출중"),(-2,"대출중"),(0,"대출중"),(1,"대출중"),(3,"반납완료"),
                 (5,"대출중"),(-7,"반납완료"),(2,"대출중"),(0,"반납완료"),(-1,"대출중")],1)]
    for name,rows in [("books",books),("loans",loans)]:
        with (folder/(name+".csv")).open("w",encoding="utf-8-sig",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    policies=[("LIB-LOAN","대출 상태 확인","대출 상태는 대출중과 반납완료로 구별한다. 기준일에서 반납기한까지의 차이만으로 반납완료 건을 연체 대상으로 포함하지 않는다.",
               "days_from_due는 교육용 자료 기준일과 반납기한의 차이다. 양수는 기한이 지난 일수, 음수는 남은 일수이며 실제 오늘의 상태가 아니다."),
              ("LIB-EXTEND","연장 검토","연장 가능 여부는 현재 대출 상태와 예약·자료 유형 조건을 함께 확인한다. 이 자료에는 예약 정보가 없다.",
               "예약 자료가 없으면 연장을 확정하지 않고 추가 확인이 필요하다고 안내한다. 현재 자료로 연장 승인을 자동 기록하지 않는다."),
              ("LIB-PRIVACY","이용 기록의 범위","교육용 표에는 이름과 연락처가 없고 역할만 있다. 역할이 같다는 이유로 같은 이용자라고 결합하지 않는다.",
               "도서 식별자와 대출 식별자를 구분한다. 같은 도서가 여러 대출에 나타날 수 있다.")]
    docs=[]
    for identity,title,a,b in policies:
        (folder/(identity+".md")).write_text(f"# {title}\n\n문서번호 {identity} · 개정 B · 현행\n\n"
            f"성격: 설계. 실제 도서관 규정이 아닌 전이 실습용 자료.\n\n## 1. 적용\n\n{a}\n\n## 2. 경계\n\n{b}\n",encoding="utf-8")
        docs.append({"id":identity,"title":title,"revision":"B","status":"current","path":f"data/transfer/{identity}.md",
                     "source":"새로 작성한 도서 대출 전이 사례","provenance":"설계: 실제 도서관 규정 아님"})
    def col(i,name,meaning,unit,kind="text"):
        return {"id":i,"name":name,"meaning":meaning,"unit":unit,"type":kind,"source":"교육용 설계","meaning_status":"documented"}
    config={"label":"도서 대출 문의 · 교육용 설계","ontology":"ontology/transfer.csv","documents":docs,
        "sources":{
        "books":{"path":"data/transfer/books.csv","table":"transfer_books","provenance":"교육용 설계: 실제 소장 자료 아님",
                 "columns":[col(601,"book_id","도서 식별자","ID"),col(602,"category","분류","범주"),col(603,"copies","소장 권수","권","number")]},
        "loans":{"path":"data/transfer/loans.csv","table":"transfer_loans","provenance":"교육용 설계: 실제 대출 기록 아님",
                 "columns":[col(701,"loan_id","대출 건 식별자","ID"),col(702,"book_id","해당 도서 식별자","ID"),
                 col(703,"borrower_role","이용자 역할; 개인 식별자 아님","역할"),
                 col(704,"days_from_due","자료 기준일에서 반납기한을 뺀 일수; 양수는 기한 경과","일","number"),
                 col(705,"state","대출중 또는 반납완료","상태")]}}}
    mapping=json.loads((APP/"mapping.json").read_text(encoding="utf-8"))
    mapping["profiles"]["transfer"]=config
    (APP/"mapping.json").write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding="utf-8")
    with (APP/"ontology/transfer.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        fields=["source","source_type","relation","target","target_type","provenance"]
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in loans:
            writer.writerow({"source":"transfer:loan:"+row["loan_id"],"source_type":"loan","relation":"borrows",
                "target":"transfer:book:"+row["book_id"],"target_type":"book","provenance":"교육용 설계: 명시 도서 키 연결"})
    (folder/"README.md").write_text("# 도서 대출 문의 자료\n\n모든 행과 규정은 교육용 설계다. 실제 도서관의 운영·개인 기록이 아니다. "
        "현재 시각이나 실제 연체 상태를 나타내지 않는다.\n\n도서·대출 건·역할의 차이를 확인하고 표 계산과 규정을 연결한다. "
        "예약 여부는 제공하지 않았다. 현재 자료에서 무엇을 답할 수 있고 어디서 추가 확인이 필요한지 판단한다. "
        "제조 서비스의 LOT·설비·알람·단위·승인 가정을 그대로 옮겨 쓰지 않는다.\n",encoding="utf-8")
    print("제조가 아닌 전이 자료 2표·3문서·관계표 작성")


if __name__=="__main__":
    main()
