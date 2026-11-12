const {chromium}=require('playwright');const fs=require('fs');const scene=process.argv[2];const name=JSON.parse(fs.readFileSync(scene)).name;
(async()=>{const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:3840,height:2160}});p.on('pageerror',e=>console.log('PE',e.message));p.on('console',m=>{if(m.type()==='error')console.log(m.text())});
await p.goto('http://localhost:8765/buffers.html?ss=2&scene='+scene);await p.waitForFunction('window.READY',null,{timeout:180000});console.log('missing',await p.evaluate('window.MISSING'));
fs.mkdirSync('out/'+name,{recursive:true});for(const [m,n] of [[0,'id'],[1,'normal'],[2,'depth']])fs.writeFileSync(`out/${name}/${n}.png`,Buffer.from(await p.evaluate(m=>window.grab(m),m),'base64'));
for(const t of await p.evaluate('window.SOLO'))fs.writeFileSync(`out/${name}/solo_${t}.png`,Buffer.from(await p.evaluate(t=>window.grabSolo(t),t),'base64'));
for(const t of await p.evaluate('window.SOLOK'))fs.writeFileSync(`out/${name}/solok_${t}.png`,Buffer.from(await p.evaluate(t=>window.grabSoloK(t),t),'base64'));
await b.close();console.log('ok')})();
