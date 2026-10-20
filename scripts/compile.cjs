const fs = require('fs');
const solc = require('solc');
const input = {language:'Solidity',sources:{'Lab.sol':{content:fs.readFileSync('contracts/Lab.sol','utf8')}},settings:{viaIR:true,optimizer:{enabled:true,runs:200},evmVersion:'paris',outputSelection:{'*':{'*':['abi','evm.bytecode']}}}};
const out = JSON.parse(solc.compile(JSON.stringify(input)));
for(const e of out.errors || []) console.error(e.formattedMessage);
if((out.errors || []).some(e=>e.severity==='error')) process.exit(1);
fs.mkdirSync('artifacts',{recursive:true});
for(const [name,c] of Object.entries(out.contracts['Lab.sol'])) fs.writeFileSync(`artifacts/${name}.json`,JSON.stringify({abi:c.abi,bytecode:'0x'+c.evm.bytecode.object,linkReferences:c.evm.bytecode.linkReferences},null,2));
console.log('Compiled lab contracts with solc '+solc.version());
