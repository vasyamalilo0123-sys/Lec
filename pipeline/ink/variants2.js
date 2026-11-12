const {chromium}=require('playwright');const fs=require('fs');const sc=JSON.parse(fs.readFileSync(process.argv[2]));
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('console',m=>{if(m.type()==='error')console.log('C',m.text())});p.on('pageerror',e=>console.log('PE',e.message));
const kof={};for(const k in sc.labels)kof[(sc.merge||{})[k]||k]=sc.parts[k];
await p.goto('http://localhost:8765/variants2.html?scene='+sc.name+'&focus='+process.argv[3]+'&kof='+encodeURIComponent(JSON.stringify(kof)));await p.waitForFunction('window.READY',null,{timeout:60000});
for(const v of 'ABCDE')fs.writeFileSync(`out/${sc.name}/variant-${v}.png`,Buffer.from(await p.evaluate(v=>window.render(v),v),'base64'));
await b.close();console.log('done')})();
