from .chain import Chain, WAD, ZERO


def deploy_uniswap(c):
    if c.path.exists():
        raise ValueError(f'{c.path} already exists; use a fresh chain or archive the old manifest explicitly')
    tokens = {s: c.deploy('LabToken', s) for s in 'ABCD'}
    for t in tokens.values():
        c.send(t.functions.mint(c.account, 10_000_000 * WAD))
    weth = c.deploy('WETH9')
    markets = []
    for label in ('main', 'arb'):
        factory = c.deploy('UniswapV2Factory', c.account)
        router = c.deploy('UniswapV2Router02', factory.address, weth.address)
        for t in tokens.values():
            c.send(t.functions.approve(router.address, 2**256-1))
        # Main graph: A-B-C-D plus a deliberately worse A-D shortcut.
        # Second independent market has cheaper A, enabling a reproducible arbitrage.
        pools = [('A','B',100_000,100_000),('B','C',100_000,100_000),('C','D',100_000,100_000),('A','D',100_000,70_000)] if label == 'main' else [('A','B',120_000,100_000)]
        for a,b,x,y in pools:
            deadline = c.w3.eth.get_block('latest').timestamp + 1200
            c.send(router.functions.addLiquidity(tokens[a].address,tokens[b].address,x*WAD,y*WAD,x*WAD,y*WAD,c.account,deadline))
        markets.append((factory.address,router.address))
    data = {'tokens':{s:t.address for s,t in tokens.items()}, 'weth':weth.address,'factory':markets[0][0],'router':markets[0][1],'arb_factory':markets[1][0],'arb_router':markets[1][1]}
    c.save(data)
    return data


def deploy_aave(c):
    d = c.load()
    if 'pool' in d:
        raise ValueError('Aave already deployed in this manifest')
    provider = c.deploy('PoolAddressesProvider','DEFI_LAB_4',c.account)
    c.send(provider.functions.setACLAdmin(c.account))
    acl = c.deploy('ACLManager',provider.address)
    c.send(provider.functions.setACLManager(acl.address))
    c.send(acl.functions.addPoolAdmin(c.account))
    implementation = c.deploy('Pool',provider.address)
    c.send(provider.functions.setPoolImpl(implementation.address))
    pool = c.contract('Pool',provider.functions.getPool().call())
    cfg_impl = c.deploy('PoolConfigurator')
    c.send(provider.functions.setPoolConfiguratorImpl(cfg_impl.address))
    cfg = c.contract('PoolConfigurator',provider.functions.getPoolConfigurator().call())
    oracle = c.deploy('LabOracle')
    c.send(provider.functions.setPriceOracle(oracle.address))
    dp = c.deploy('AaveProtocolDataProvider',provider.address)
    c.send(provider.functions.setPoolDataProvider(dp.address))
    a = c.deploy('AToken',pool.address)
    stable = c.deploy('StableDebtToken',pool.address)
    variable = c.deploy('VariableDebtToken',pool.address)
    ray = 10**27
    strategy = c.deploy('DefaultReserveInterestRateStrategy',provider.address,8*ray//10,0,4*ray//100,75*ray//100,2*ray//100,75*ray//100,2*ray//100,5*ray//100,2*ray//10)
    asset = d['tokens']['A']
    inputs = (a.address,stable.address,variable.address,18,strategy.address,asset,c.account,ZERO,'Lab Aave A','aA','Lab Variable A','vA','Lab Stable A','sA',b'')
    c.send(cfg.functions.initReserves([inputs]))
    c.send(cfg.functions.setReserveFlashLoaning(asset,True))
    c.send(cfg.functions.updateFlashloanPremiumTotal(5))  # 0.05%; flashLoanSimple does not waive fees.
    token = c.contract('LabToken',asset)
    c.send(token.functions.approve(pool.address,1_000_000*WAD))
    c.send(pool.functions.supply(asset,1_000_000*WAD,c.account,0))
    receiver = c.deploy('FlashArbitrage',pool.address,d['router'],d['arb_router'])
    d.update(provider=provider.address,pool=pool.address,configurator=cfg.address,oracle=oracle.address,receiver=receiver.address,libraries=c.libraries)
    c.save(d)
    return d
