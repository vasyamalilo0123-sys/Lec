const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('console',m=>{if(m.type()==='error')console.log('C',m.text())});p.on('pageerror',e=>console.log('PE',e.message));
await p.goto('http://localhost:8765/variants.html');await p.waitForFunction('window.READY',null,{timeout:60000});
for(const v of [1,2,3,4,5])fs.writeFileSync(`variant-${v}.png`,Buffer.from(await p.evaluate(v=>window.render(v),v),'base64'));
await b.close();console.log('done')})();
