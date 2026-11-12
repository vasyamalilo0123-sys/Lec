import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const man=JSON.parse(fs.readFileSync('data/manifest.json'));const name={};man.structures.forEach(s=>(s.meshes||[]).forEach(m=>name[m]=s.id.split('.')[1]));
const want=new Set([1629,1630,1631,1632,1633,1634,1635,1636,1638,1639,1652,1663,1664,1665,1717,1752,2073,2075,2076,2077,2078,2079,2083,2089,2093,2176,2282]);
fs.mkdirSync('obj',{recursive:true});
for(const f of ['arterial_system','systemic_arteries','right_subclavian_artery--pulmonary_veins','systemic_veins.2','superior_vena_cava']){
  const doc=await io.read('data/standard/cardiovascular/'+f+'.glb');
  for(const node of doc.getRoot().listNodes()){const mesh=node.getMesh();if(!mesh)continue;const M=node.getWorldMatrix();
    for(const p of mesh.listPrimitives()){const P=p.getAttribute('POSITION'),I=p.getAttribute('_ID'),idx=p.getIndices().getArray();
      const by={};for(let i=0;i<idx.length;i+=3){const k=I.getElement(idx[i],[])[0];if(want.has(k))(by[k]||(by[k]=[])).push(idx[i],idx[i+1],idx[i+2])}
      for(const k in by){const map=new Map();let v='',fc='';const e=[];
        for(let i=0;i<by[k].length;i++){const s=by[k][i];if(!map.has(s)){map.set(s,map.size+1);P.getElement(s,e);
          const x=M[0]*e[0]+M[4]*e[1]+M[8]*e[2]+M[12],y=M[1]*e[0]+M[5]*e[1]+M[9]*e[2]+M[13],z=M[2]*e[0]+M[6]*e[1]+M[10]*e[2]+M[14];v+=`v ${x} ${y} ${z}\n`}
          if(i%3==2)fc+=`f ${map.get(by[k][i-2])} ${map.get(by[k][i-1])} ${map.get(s)}\n`}
        fs.writeFileSync(`obj/${k}_${name[k]}.obj`,v+fc);console.log(k,name[k],map.size)}}}}
