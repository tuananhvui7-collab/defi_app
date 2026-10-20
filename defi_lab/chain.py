import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
ZERO = '0x' + '00' * 20
WAD = 10**18


def artifact(name):
    local = ROOT / 'artifacts' / f'{name}.json'
    if local.exists():
        return json.loads(local.read_text())
    for package in ('@uniswap/v2-core', '@uniswap/v2-periphery'):
        p = ROOT / 'node_modules' / package / 'build' / f'{name}.json'
        if p.exists():
            return json.loads(p.read_text())
    matches = list((ROOT / 'node_modules/@aave/core-v3/artifacts/contracts').rglob(f'{name}.json'))
    if len(matches) != 1:
        raise ValueError(f'Artifact {name} not found or ambiguous; run npm ci && npm run compile')
    return json.loads(matches[0].read_text())


class Chain:
    def __init__(self):
        rpc = os.getenv('RPC_URL', 'http://127.0.0.1:8545')
        self.w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.chain_id = self.w3.eth.chain_id
        expected = int(os.getenv('LAB_CHAIN_ID', '1337'))
        if self.chain_id not in (1337, 31337, 11155111) or self.chain_id != expected:
            raise ValueError('Only local 1337/31337 or Sepolia 11155111 allowed; LAB_CHAIN_ID must match RPC')
        key = os.getenv('PRIVATE_KEY')
        self.signer = self.w3.eth.account.from_key(key) if key else None
        if self.chain_id == 11155111 and not key:
            raise ValueError('Sepolia requires PRIVATE_KEY from secure local environment, never chat')
        if self.chain_id != 11155111 and urlsplit(rpc).hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('Unlocked dev accounts require a loopback RPC')
        self.account = self.signer.address if key else self.w3.eth.accounts[0]
        self.path = ROOT / '.local' / f'deployment-{self.chain_id}.json'
        self.libraries = {}

    def contract(self, name, address):
        return self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=artifact(name)['abi'])

    def send(self, fn, *, gas=None):
        tx = {'from': self.account, 'chainId': self.chain_id, 'nonce': self.w3.eth.get_transaction_count(self.account, 'pending')}
        tx['gas'] = gas or int(fn.estimate_gas({'from': self.account}) * 1.2)
        if self.signer:
            built = fn.build_transaction(tx)
            signed = self.signer.sign_transaction(built)
            h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        else:
            h = fn.transact(tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(h, timeout=180)
        self.path.parent.mkdir(exist_ok=True)
        evidence = {'chain_id': self.chain_id, 'tx': receipt.transactionHash.hex(), 'block': receipt.blockNumber, 'status': receipt.status, 'gas_used': receipt.gasUsed, 'contract': receipt.contractAddress}
        with (self.path.parent / f'transactions-{self.chain_id}.jsonl').open('a') as log:
            log.write(json.dumps(evidence) + '\n')
        if receipt.status != 1:
            raise RuntimeError(f'Transaction reverted: {h.hex()}')
        return receipt

    def deploy(self, name, *args):
        a = artifact(name)
        bytecode = a['bytecode'].removeprefix('0x')
        for source, libs in a.get('linkReferences', {}).items():
            for lib, spots in libs.items():
                if lib not in self.libraries:
                    self.libraries[lib] = self.deploy(lib).address
                address = self.libraries[lib][2:]
                for spot in spots:
                    start, length = spot['start']*2, spot['length']*2
                    bytecode = bytecode[:start] + address.zfill(length) + bytecode[start+length:]
        c = self.w3.eth.contract(abi=a['abi'], bytecode='0x'+bytecode)
        receipt = self.send(c.constructor(*args))
        print(f'Deployed {name}: {receipt.contractAddress} tx={receipt.transactionHash.hex()}', flush=True)
        return self.contract(name, receipt.contractAddress)

    def save(self, data):
        self.path.parent.mkdir(exist_ok=True)
        data.update(chain_id=self.chain_id, genesis=self.w3.eth.get_block(0).hash.hex(), deployer=self.account)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, indent=2))
        temp.replace(self.path)

    def load(self):
        data = json.loads(self.path.read_text())
        if data['genesis'] != self.w3.eth.get_block(0).hash.hex():
            raise ValueError('Deployment belongs to a different chain; redeploy')
        for address in [data['router'], data['factory'], *data['tokens'].values()]:
            if not self.w3.eth.get_code(address):
                raise ValueError('Missing deployed bytecode; redeploy after chain reset')
        return data
