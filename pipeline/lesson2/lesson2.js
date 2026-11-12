const {chromium}=require('playwright');const fs=require('fs');const mode=process.argv[2]||'stills',FPS=25;
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('console',m=>{if(m.type()==='error')console.log('C',m.text())});p.on('pageerror',e=>console.log('PE',e.message));
await p.goto('http://localhost:8765/lesson2.html');await p.waitForFunction('window.READY',null,{timeout:120000});const DUR=await p.evaluate('window.DUR');
fs.mkdirSync('l2',{recursive:true});
if(mode==='stills'){for(const t of (process.argv[3]||'4,20,28.5,42,50,58,64,69,75').split(',').map(Number)){await p.evaluate(t=>window.renderAt(t),t);await p.screenshot({path:`l2/s_${t}.jpg`,type:'jpeg',quality:92})}}
else{fs.rmSync('l2f',{recursive:true,force:true});fs.mkdirSync('l2f');const n=FPS*DUR;for(let i=0;i<n;i++){await p.evaluate(t=>window.renderAt(t),i/FPS);await p.screenshot({path:`l2f/f${String(i).padStart(5,'0')}.jpg`,type:'jpeg',quality:95})}}
await b.close();console.log('done')})();
