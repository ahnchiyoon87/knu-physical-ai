// Parse and compile every supplied Vue SFC without running the service or models.
const fs=require('node:fs'),path=require('node:path')
const root=path.resolve(__dirname,'..'),app=path.join(root,'10_실습','완성본','equipment-assistant')
const compiler=require(path.join(app,'frontend/node_modules/@vue/compiler-sfc'))
const manifest=JSON.parse(fs.readFileSync(path.join(root,'30_기록','출발본_매니페스트.json'),'utf8'))
const completed=path.join(root,'30_기록','완성본_매니페스트.json')
if(fs.existsSync(completed))manifest.push(...JSON.parse(fs.readFileSync(completed,'utf8')))
const folders=[app,...manifest.filter(x=>x.features.length).map(x=>path.join(root,x.folder))]
const errors=[];let files=0
for(const folder of folders){
 for(const name of fs.readdirSync(path.join(folder,'frontend/src')).filter(x=>x.endsWith('.vue'))){
  const filename=path.join(folder,'frontend/src',name),source=fs.readFileSync(filename,'utf8')
  try{
   const parsed=compiler.parse(source,{filename});if(parsed.errors.length)throw Error(parsed.errors.join('; '))
   const script=compiler.compileScript(parsed.descriptor,{id:'verify-'+files})
   const template=compiler.compileTemplate({source:parsed.descriptor.template.content,filename,id:'verify-'+files,
     compilerOptions:{bindingMetadata:script.bindings}})
   if(template.errors.length)throw Error(template.errors.join('; '))
   for(const match of source.matchAll(/from\s+['"](\.\/?[^'"]+)['"]/g)){
     const target=path.resolve(path.dirname(filename),match[1]);if(![target,target+'.js',target+'.vue'].some(fs.existsSync))throw Error('missing import '+match[1])
   }
   files++
  }catch(e){errors.push({file:path.relative(root,filename),error:e.message})}
 }
}
const result={scope:'Vue parse, script/template compilation and local import presence; no GUI interaction',files,errors}
fs.writeFileSync(path.join(root,'30_기록','Vue_구문검사.json'),JSON.stringify(result,null,2))
console.log(JSON.stringify(result,null,2));process.exit(errors.length?1:0)
