import pytest
from backend.detect.provenance import bind_predictions

IMPORTED={"id":"import-a","file_hash":"file-a","mapping_hash":"map-a"}

def prediction(number):
    return {"row_no":number,"expected":1,"predicted":0}


def test_actual_lot_and_absent_lot_are_distinct():
    result,edges=bind_predictions({"predictions":[prediction(2),prediction(4)]},
                                 [{"row_no":2,"lot_id":"7"},{"row_no":4,"lot_id":None}],"p","s",IMPORTED,"run-a")
    assert result["predictions"][0]["row_id"]=="p:s:row:2"
    assert result["predictions"][0]["lot_target"]=="p:s:lot:7"
    assert result["predictions"][1]["lot_target"] is None
    assert result["input_import"]==IMPORTED
    assert [(e["source"],e["target"]) for e in edges]==[("run-a","p:s:row:2"),("p:s:row:2","p:s:lot:7"),("run-a","p:s:row:4")]
    assert edges[1]["provenance"]=="import=import-a"


def test_same_row_number_in_different_source_does_not_merge():
    ids=[]
    for source in ["s1","s2"]:
        result,_=bind_predictions({"predictions":[prediction(1)]},[{"row_no":1}],"p",source,IMPORTED,"run")
        ids.append(result["predictions"][0]["row_id"])
    assert ids[0]!=ids[1]


@pytest.mark.parametrize("rows,predictions,imported", [
    ([{"row_no":1},{"row_no":1}],[prediction(1)],IMPORTED),
    ([{"row_no":1}],[prediction(2)],IMPORTED),
    ([{"row_no":1}],[prediction(1),prediction(1)],IMPORTED),
    ([{"row_no":1}],[prediction(1)],{}),
])
def test_invalid_origin_is_not_invented(rows,predictions,imported):
    with pytest.raises(ValueError):
        bind_predictions({"predictions":predictions},rows,"p","s",imported,"run")
