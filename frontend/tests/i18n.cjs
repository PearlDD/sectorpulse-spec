const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const React = require('react')
const {renderToStaticMarkup} = require('react-dom/server')
function load(filename) {
  const js=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src',filename),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText
  const module={exports:{}}
  new Function('require','module','exports',js)(name=>name==='./translations'?load('translations.ts'):require(name),module,module.exports)
  return module.exports
}
const {translate,LanguageContext,Localized}=load('i18n.tsx')
assert.equal(translate('强势升温','en'),'Heating up')
assert.equal(translate('强势升温','zh'),'强势升温')
assert.equal(translate('中文','en'),'中文')
assert.equal(translate('未来 90 天','en'),'Next 90 days')
assert.equal(translate('  地缘政治  ','en'),'  Geopolitics  ')
const element=React.createElement(LanguageContext.Provider,{value:'en'},React.createElement(Localized,null,
  React.createElement('select',{'aria-label':'板块范围',defaultValue:'强势升温'},React.createElement('option',{value:'强势升温'},'强势升温'))))
const html=renderToStaticMarkup(element)
assert(html.includes('aria-label="Sector scope"'))
assert(html.includes('value="强势升温"'))
assert(html.includes('Heating up'))
console.log('Language labels, whitespace, filter identity and accessible names passed.')
