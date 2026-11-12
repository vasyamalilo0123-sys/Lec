const {chromium}=require('playwright');const fs=require('fs');
const mode=process.argv[2]||'stills',FPS=25,DUR=26;
(async()=>{const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:1920,height:1080}});
p.on('console',m=>{if(m.type()==='error')console.log('C',m.text())});p.on('pageerror',e=>console.log('PE',e.message));
await p.goto('http://localhost:8765/film.html');await p.waitForFunction('window.READY',null,{timeout:180000});
if(mode==='stills'){const t0=Date.now();for(const t of [3,8.5,11.6,15,21,25.5]){fs.writeFileSync(`st_${t}.jpg`,Buffer.from(await p.evaluate(t=>window.frame(t),t),'base64'))}console.log('ms/frame',(Date.now()-t0)/6)}
else{fs.mkdirSync('frames',{recursive:true});const n=FPS*DUR;for(let i=0;i<n;i++){fs.writeFileSync(`frames/f${String(i).padStart(5,'0')}.jpg`,Buffer.from(await p.evaluate(t=>window.frame(t,.95),i/FPS),'base64'));if(i%100===0)console.log('frame',i,'/',n)}}
await b.close()})();
