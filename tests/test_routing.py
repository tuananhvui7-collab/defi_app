import pytest
from defi_lab.routing import Edge, amount_out, best_route
from defi_lab.cli import units


def test_exact_fee_rounding_and_price_impact():
    assert amount_out(1000,10000,10000) == 906
    assert amount_out(2000,10000,10000) < 2*amount_out(1000,10000,10000)
    with pytest.raises(ValueError): amount_out(0,100,100)


def test_trade_size_changes_best_route():
    graph = {'A':[Edge('D',100000,80000,'ad'),Edge('B',1000,2000,'ab')], 'B':[Edge('D',2000,2000,'bd')]}
    assert best_route(graph,'A','D',10)[1] == ['A','B','D']
    assert best_route(graph,'A','D',5000)[1] == ['A','D']
    assert best_route(graph,'A','D',10,1)[1] == ['A','D']


def test_disconnected_empty_and_cycle():
    graph = {'A':[Edge('B',100,100,'ab')], 'B':[Edge('A',100,100,'ab')]}
    with pytest.raises(ValueError,match='No liquid route'): best_route(graph,'A','D',10)
    with pytest.raises(ValueError): best_route(graph,'A','A',10)
    with pytest.raises(ValueError): best_route(graph,'A','B',10,7)
    with pytest.raises(ValueError): best_route({'A':[Edge('B',0,10,'ab')]},'A','B',10)


def test_decimal_parser():
    assert units('0.000000000000000001') == 1
    assert units('1.5') == 15*10**17
    for invalid in ('nan','inf','0','-1','0.0000000000000000001'):
        with pytest.raises(Exception): units(invalid)
