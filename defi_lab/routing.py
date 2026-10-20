from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    target: str
    reserve_in: int
    reserve_out: int
    pair: str


def amount_out(amount, reserve_in, reserve_out):
    """Exact integer formula from Uniswap V2, 0.30% swap fee."""
    if amount <= 0 or reserve_in <= 0 or reserve_out <= 0:
        raise ValueError('Amount and reserves must be positive')
    fee_amount = amount * 997
    return fee_amount * reserve_out // (reserve_in * 1000 + fee_amount)


def best_route(graph, start, end, amount, max_hops=3):
    """Enumerate simple paths; maximize raw output for this amount, ignoring gas.

    Bounded DFS is exact within the supplied graph/hop bound. No reused tokens
    or pairs: each edge sees unchanged reserves. Not Dijkstra: weights depend
    nonlinearly on trade size. Exponential; appropriate for a four-token lab.
    """
    if start == end or amount <= 0 or not 1 <= max_hops <= 6:
        raise ValueError('Distinct endpoints, positive amount, 1..6 hops required')
    candidates = []

    def visit(token, value, path, pairs):
        if token == end:
            candidates.append((value, path))
            return
        if len(path)-1 == max_hops:
            return
        for edge in graph.get(token, []):
            if edge.target in path or edge.pair in pairs:
                continue
            if min(edge.reserve_in, edge.reserve_out) <= 0:
                continue
            output = amount_out(value, edge.reserve_in, edge.reserve_out)
            if output:
                visit(edge.target,output,path+[edge.target],pairs | {edge.pair})

    visit(start,amount,[start],set())
    if not candidates:
        raise ValueError('No liquid route within hop limit')
    return max(candidates,key=lambda x:(x[0],-len(x[1])))


def snapshot_graph(c, d):
    """Read all listed factory pairs at one block, orient reserves by token0."""
    block = c.w3.eth.block_number
    factory = c.contract('UniswapV2Factory',d['factory'])
    symbols = {v.lower():k for k,v in d['tokens'].items()}
    graph = {s:[] for s in symbols.values()}
    for i in range(factory.functions.allPairsLength().call(block_identifier=block)):
        address = factory.functions.allPairs(i).call(block_identifier=block)
        pair = c.contract('UniswapV2Pair',address)
        t0 = pair.functions.token0().call(block_identifier=block).lower()
        t1 = pair.functions.token1().call(block_identifier=block).lower()
        if t0 not in symbols or t1 not in symbols:
            continue
        r0,r1,_ = pair.functions.getReserves().call(block_identifier=block)
        a,b = symbols[t0],symbols[t1]
        graph[a].append(Edge(b,r0,r1,address))
        graph[b].append(Edge(a,r1,r0,address))
    return graph, block
