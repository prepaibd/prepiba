// stdin: JSON array of {tex, display}; stdout: JSON array of error strings (null = ok)
const katex = require('katex');
let s=''; process.stdin.on('data',d=>s+=d).on('end',()=>{
  const items=JSON.parse(s);
  const out=items.map(it=>{try{katex.renderToString(it.tex,{throwOnError:true,displayMode:!!it.display,strict:'ignore'});return null}catch(e){return String(e.message)}});
  process.stdout.write(JSON.stringify(out));
});
