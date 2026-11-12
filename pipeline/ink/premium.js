const {chromium}=require('playwright');const fs=require('fs');const name=process.argv[2];
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('console',m=>{if(m.type()==='error'&&!/404/.test(m.text()))console.log('C',m.text())});p.on('pageerror',e=>console.log('PE',e.message));
await p.goto('http://localhost:8765/premium.html?scene='+name);await p.waitForFunction('window.READY',null,{timeout:120000});
for(const v of [1,2,3,4,5])fs.writeFileSync(`out/${name}/premium-${v}.png`,Buffer.from(await p.evaluate(v=>window.render(v),v),'base64'));
await b.close();console.log('done')})();
