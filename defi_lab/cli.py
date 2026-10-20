import argparse
import json
from decimal import Decimal, InvalidOperation

from .chain import Chain, WAD
from .deploy import deploy_uniswap, deploy_aave
from .routing import best_route, snapshot_graph


def units(value):
    try:
        n = Decimal(value) * WAD
        if not n.is_finite() or n <= 0 or n != n.to_integral_value():
            raise ValueError
        return int(n)
    except (InvalidOperation, ValueError):
        raise argparse.ArgumentTypeError('Positive amount with at most 18 decimals required')


def execute_swap(c,d,path,amount,slippage_bps=50):
    if not 0 <= slippage_bps <= 1000:
        raise ValueError('Slippage must be 0..1000 basis points')
    if not 2 <= len(path) <= 7 or len(set(path)) != len(path):
        raise ValueError('Use a simple path with 1..6 hops')
    addresses = [d['tokens'][s] for s in path]
    router = c.contract('UniswapV2Router02',d['router'])
    quote = router.functions.getAmountsOut(amount,addresses).call()[-1]
    minimum = quote * (10000-slippage_bps)//10000
    if minimum <= 0:
        raise ValueError('Output too small')
    source = c.contract('LabToken',addresses[0])
    target = c.contract('LabToken',addresses[-1])
    if source.functions.allowance(c.account,router.address).call() < amount:
        c.send(source.functions.approve(router.address,amount))
    before_in = source.functions.balanceOf(c.account).call()
    before_out = target.functions.balanceOf(c.account).call()
    deadline = c.w3.eth.get_block('latest').timestamp + 300
    receipt = c.send(router.functions.swapExactTokensForTokens(amount,minimum,addresses,c.account,deadline))
    actual = target.functions.balanceOf(c.account).call()-before_out
    if source.functions.balanceOf(c.account).call() != before_in-amount or actual < minimum:
        raise AssertionError('Unexpected swap balance deltas')
    return {'tx':receipt.transactionHash.hex(),'block':receipt.blockNumber,'path':path,'amount_in':amount,'quoted_out':quote,'min_out':minimum,'actual_out':actual,'gas_used':receipt.gasUsed}


def execute_flash(c,d,amount,min_profit=1):
    pool = c.contract('Pool',d['pool'])
    one = c.contract('UniswapV2Router02',d['router'])
    two = c.contract('UniswapV2Router02',d['arb_router'])
    a,b = d['tokens']['A'],d['tokens']['B']
    middle = one.functions.getAmountsOut(amount,[a,b]).call()[-1]
    output = two.functions.getAmountsOut(middle,[b,a]).call()[-1]
    premium = (amount*pool.functions.FLASHLOAN_PREMIUM_TOTAL().call()+5000)//10000
    if output < amount+premium+min_profit:
        raise ValueError('Current reserves do not offer the requested profit')
    receiver = c.contract('FlashArbitrage',d['receiver'])
    before = c.contract('LabToken',a).functions.balanceOf(receiver.address).call()
    receipt = c.send(receiver.functions.run(a,b,amount,middle*9950//10000,output*9950//10000,min_profit,c.w3.eth.get_block('latest').timestamp+300))
    after = c.contract('LabToken',a).functions.balanceOf(receiver.address).call()
    # Parse only the receiver event; unrelated ERC20 events are ignored.
    from web3.logs import DISCARD
    event = receiver.events.Executed().process_receipt(receipt,errors=DISCARD)[0]['args']
    if after-before != event['profit'] or event['premium'] != premium:
        raise AssertionError('Flash-loan profit/premium mismatch')
    return {'tx':receipt.transactionHash.hex(),'amount':amount,'premium':premium,'profit':after-before,'gas_used':receipt.gasUsed}


def main():
    p = argparse.ArgumentParser(description='DeFi Lab 4: Python CLI (local / Sepolia only)')
    sub = p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('status')
    sub.add_parser('deploy-uniswap')
    sub.add_parser('deploy-aave')
    s = sub.add_parser('swap')
    s.add_argument('--path',nargs='+',required=True,choices=list('ABCD'))
    s.add_argument('--amount',type=units,required=True)
    s.add_argument('--slippage-bps',type=int,default=50)
    r = sub.add_parser('route')
    r.add_argument('--source',choices=list('ABCD'),default='A')
    r.add_argument('--target',choices=list('ABCD'),default='D')
    r.add_argument('--amount',type=units,required=True)
    r.add_argument('--max-hops',type=int,default=3)
    r.add_argument('--execute',action='store_true')
    f = sub.add_parser('flash')
    f.add_argument('--amount',type=units,default=100*WAD)
    f.add_argument('--min-profit',type=units,default=WAD)
    args = p.parse_args()
    c = Chain()
    if args.cmd == 'status':
        result = {'client':c.w3.client_version,'chain_id':c.chain_id,'block':c.w3.eth.block_number,'account':c.account,'gas_balance_wei':c.w3.eth.get_balance(c.account),'deployment_file':str(c.path)}
    elif args.cmd == 'deploy-uniswap':
        result = deploy_uniswap(c)
    elif args.cmd == 'deploy-aave':
        result = deploy_aave(c)
    else:
        d = c.load()
        if args.cmd == 'swap':
            result = execute_swap(c,d,args.path,args.amount,args.slippage_bps)
        elif args.cmd == 'route':
            graph,block = snapshot_graph(c,d)
            amount,path = best_route(graph,args.source,args.target,args.amount,args.max_hops)
            result = {'block':block,'path':path,'quoted_out':amount,'objective':'maximum output before gas; main factory only'}
            if args.execute:
                result['execution'] = execute_swap(c,d,path,args.amount)
        else:
            result = execute_flash(c,d,args.amount,args.min_profit)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
