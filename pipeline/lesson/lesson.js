const {chromium}=require('playwright');const fs=require('fs');const mode=process.argv[2]||'stills',FPS=25;
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('console',m=>{if(m.type()==='error')console.log('C',m.text())});p.on('pageerror',e=>console.log('PE',e.message));
await p.goto('http://localhost:8765/lesson.html');await p.waitForFunction('window.READY',null,{timeout:120000});const DUR=await p.evaluate('window.DUR');
fs.mkdirSync('lstills',{recursive:true});
if(mode==='stills'){for(const t of (process.argv[3]||'4,15,23.5,36,45,53,58,65,70').split(',').map(Number))fs.writeFileSync(`lstills/s_${t}.jpg`,Buffer.from(await p.evaluate(t=>window.frame(t),t),'base64'))}
else{fs.rmSync('lframes',{recursive:true,force:true});fs.mkdirSync('lframes');const n=FPS*DUR;for(let i=0;i<n;i++)fs.writeFileSync(`lframes/f${String(i).padStart(5,'0')}.jpg`,Buffer.from(await p.evaluate(t=>window.frame(t),i/FPS),'base64'))}
await b.close();console.log('done')})();
