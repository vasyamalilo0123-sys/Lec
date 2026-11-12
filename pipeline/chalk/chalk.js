const {chromium}=require('playwright');const fs=require('fs');
const mode=process.argv[2]||'stills',FPS=25,DUR=23;
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('console',m=>{if(m.type()==='error')console.log('C',m.text())});p.on('pageerror',e=>console.log('PE',e.message));
await p.goto('http://localhost:8765/chalk.html');await p.waitForFunction('window.READY',null,{timeout:60000});
if(mode==='stills'){for(const t of [4.5,22]){fs.writeFileSync(`ch_${t}.jpg`,Buffer.from(await p.evaluate(t=>window.frame(t),t),'base64'))}}
else{fs.rmSync('cframes',{recursive:true,force:true});fs.mkdirSync('cframes');const n=FPS*DUR;for(let i=0;i<n;i++)fs.writeFileSync(`cframes/f${String(i).padStart(5,'0')}.jpg`,Buffer.from(await p.evaluate(t=>window.frame(t),i/FPS),'base64'))}
await b.close();console.log('done')})();
