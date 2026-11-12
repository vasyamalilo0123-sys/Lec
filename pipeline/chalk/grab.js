const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:1920,height:1080}});p.on('pageerror',e=>console.log('PE',e.message));p.on('console',m=>{if(m.type()==='error')console.log(m.text())});
await p.goto('http://localhost:8765/buffers.html');await p.waitForFunction('window.READY',null,{timeout:180000});
fs.mkdirSync('buf',{recursive:true});for(const [m,n] of [[0,'id'],[1,'normal'],[2,'depth']])fs.writeFileSync(`buf/${n}.png`,Buffer.from(await p.evaluate(m=>window.grab(m),m),'base64'));
await b.close();console.log('ok')})();
