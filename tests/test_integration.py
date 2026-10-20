"""Opt-in transactions on an already-deployed, disposable local Geth chain."""
import os
import pytest

from defi_lab.chain import Chain, WAD
from defi_lab.cli import execute_swap, execute_flash
from defi_lab.routing import best_route, snapshot_graph

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.getenv('RUN_INTEGRATION') != '1',reason='Set RUN_INTEGRATION=1 after deploying the disposable local chain')]


@pytest.fixture(scope='module')
def lab():
    c = Chain()
    assert c.chain_id in (1337,31337), 'Integration suite only runs on disposable local chains'
    return c,c.load()


def test_real_bytecode_and_aave_liquidity(lab):
    c,d = lab
    assert 'Geth' in c.w3.client_version
    for key in ('factory','router','arb_router','provider','pool','receiver'):
        assert len(c.w3.eth.get_code(d[key])) > 0
    pool = c.contract('Pool',d['pool'])
    reserve = pool.functions.getReserveData(d['tokens']['A']).call()
    atoken = reserve[8]
    a = c.contract('LabToken',d['tokens']['A'])
    assert a.functions.balanceOf(atoken).call() >= 1_000_000*WAD
    assert pool.functions.FLASHLOAN_PREMIUM_TOTAL().call() == 5
    assert c.contract('AToken',atoken).functions.balanceOf(c.account).call() >= 1_000_000*WAD


def test_single_pool_swap_and_invariant(lab):
    c,d = lab
    factory = c.contract('UniswapV2Factory',d['factory'])
    pair = c.contract('UniswapV2Pair',factory.functions.getPair(d['tokens']['A'],d['tokens']['B']).call())
    x,y,_ = pair.functions.getReserves().call()
    result = execute_swap(c,d,['A','B'],10*WAD)
    assert result['actual_out'] == result['quoted_out'] > 0
    xx,yy,_ = pair.functions.getReserves().call()
    assert xx*yy >= x*y


def test_three_pool_swap(lab):
    c,d = lab
    result = execute_swap(c,d,list('ABCD'),10*WAD)
    assert result['actual_out'] == result['quoted_out'] > 0
    pair_abi = c.contract('UniswapV2Pair',d['factory']).abi
    from web3.logs import DISCARD
    logs = c.w3.eth.contract(abi=pair_abi).events.Swap().process_receipt(c.w3.eth.get_transaction_receipt(result['tx']),errors=DISCARD)
    assert len(logs) == 3


def test_route_matches_router_and_execution(lab):
    c,d = lab
    graph,block = snapshot_graph(c,d)
    amount,path = best_route(graph,'A','D',10*WAD)
    router = c.contract('UniswapV2Router02',d['router'])
    assert path == list('ABCD')
    assert amount == router.functions.getAmountsOut(10*WAD,[d['tokens'][s] for s in path]).call(block_identifier=block)[-1]
    assert amount > router.functions.getAmountsOut(10*WAD,[d['tokens'][s] for s in 'AD']).call(block_identifier=block)[-1]
    assert execute_swap(c,d,path,10*WAD)['actual_out'] == amount


def balances(c,d):
    return [c.contract('LabToken',a).functions.balanceOf(d['receiver']).call() for a in d['tokens'].values()]


def reserves(c,d):
    result = []
    for key in ('factory','arb_factory'):
        f = c.contract('UniswapV2Factory',d[key])
        for i in range(f.functions.allPairsLength().call()):
            p = c.contract('UniswapV2Pair',f.functions.allPairs(i).call())
            result.append(p.functions.getReserves().call()[:2])
    return result


def test_flash_profit_and_pool_repaid(lab):
    c,d = lab
    pool = c.contract('Pool',d['pool'])
    atoken = pool.functions.getReserveData(d['tokens']['A']).call()[8]
    token = c.contract('LabToken',d['tokens']['A'])
    before = token.functions.balanceOf(atoken).call()
    result = execute_flash(c,d,100*WAD,WAD)
    assert result['profit'] > WAD
    assert result['premium'] == 5*10**16
    assert token.functions.balanceOf(atoken).call() == before+result['premium']


def test_unprofitable_flash_rolls_back_even_with_prefunding(lab):
    c,d = lab
    # A prefunded receiver must not count its existing tokens as new profit.
    token = c.contract('LabToken',d['tokens']['A'])
    c.send(token.functions.transfer(d['receiver'],5000*WAD))
    before_b = balances(c,d)
    before_r = reserves(c,d)
    pool = c.contract('Pool',d['pool'])
    atoken = pool.functions.getReserveData(d['tokens']['A']).call()[8]
    before_pool = token.functions.balanceOf(atoken).call()
    receiver = c.contract('FlashArbitrage',d['receiver'])
    fn = receiver.functions.run(d['tokens']['A'],d['tokens']['B'],100*WAD,1,1,1000*WAD,c.w3.eth.get_block('latest').timestamp+300)
    # Confirm the semantic revert reason, then submit an actual reverting tx.
    with pytest.raises(Exception,match='unprofitable'):
        fn.call({'from':c.account})
    with pytest.raises(RuntimeError,match='reverted'):
        c.send(fn,gas=2_000_000)
    assert balances(c,d) == before_b
    assert reserves(c,d) == before_r
    assert token.functions.balanceOf(atoken).call() == before_pool


def test_unauthorized_flash_callback_reverts(lab):
    c,d = lab
    receiver = c.contract('FlashArbitrage',d['receiver'])
    fn = receiver.functions.executeOperation(d['tokens']['A'],WAD,1,receiver.address,b'')
    with pytest.raises(Exception,match='unauthorized callback'):
        fn.call({'from':c.account})
    with pytest.raises(RuntimeError,match='reverted'):
        c.send(fn,gas=200_000)


def test_slippage_and_expired_deadline_revert(lab):
    c,d = lab
    router = c.contract('UniswapV2Router02',d['router'])
    path = [d['tokens'][s] for s in 'AB']
    fn = router.functions.swapExactTokensForTokens(WAD,10**30,path,c.account,c.w3.eth.get_block('latest').timestamp+300)
    with pytest.raises(Exception,match='INSUFFICIENT_OUTPUT_AMOUNT'):
        fn.call({'from':c.account})
    with pytest.raises(RuntimeError,match='reverted'): c.send(fn,gas=500_000)
    expired = router.functions.swapExactTokensForTokens(WAD,1,path,c.account,1)
    with pytest.raises(Exception,match='EXPIRED'):
        expired.call({'from':c.account})
    with pytest.raises(RuntimeError,match='reverted'): c.send(expired,gas=500_000)


def test_signed_python_transaction_and_owner_guard(lab):
    c,d = lab
    # Disposable local signer stays in memory; no real wallet or key file involved.
    signed_chain = Chain()
    signed_chain.signer = c.w3.eth.account.create()
    signed_chain.account = signed_chain.signer.address
    funding = c.w3.eth.send_transaction({'from':c.account,'to':signed_chain.account,'value':WAD//10})
    assert c.w3.eth.wait_for_transaction_receipt(funding).status == 1
    token = c.contract('LabToken',d['tokens']['A'])
    c.send(token.functions.transfer(signed_chain.account,WAD))
    receipt = signed_chain.send(token.functions.approve(d['router'],WAD))
    assert receipt.status == 1
    assert token.functions.allowance(signed_chain.account,d['router']).call() == WAD
    receiver = c.contract('FlashArbitrage',d['receiver'])
    fn = receiver.functions.run(d['tokens']['A'],d['tokens']['B'],WAD,1,1,1,c.w3.eth.get_block('latest').timestamp+300)
    with pytest.raises(Exception,match='owner/active'):
        fn.call({'from':signed_chain.account})
    with pytest.raises(RuntimeError,match='reverted'):
        signed_chain.send(fn,gas=200_000)


def test_flash_over_available_liquidity_reverts(lab):
    c,d = lab
    before = reserves(c,d),balances(c,d)
    receiver = c.contract('FlashArbitrage',d['receiver'])
    fn = receiver.functions.run(d['tokens']['A'],d['tokens']['B'],2_000_000*WAD,1,1,1,c.w3.eth.get_block('latest').timestamp+300)
    with pytest.raises(RuntimeError,match='reverted'):
        c.send(fn,gas=2_000_000)
    assert (reserves(c,d),balances(c,d)) == before
