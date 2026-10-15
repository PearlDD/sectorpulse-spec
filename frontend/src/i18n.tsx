import { Children, cloneElement, createContext, isValidElement, useContext } from 'react'
import type { ReactNode } from 'react'
import catalogue from './translations'

export type Language = 'zh' | 'en'
export const LanguageContext = createContext<Language>('zh')
export const useLanguage = () => useContext(LanguageContext)
const phrases = Object.entries(catalogue).sort(([a],[b]) => b.length-a.length)
export function translate(value: string, language: Language): string {
  if(language==='zh' || value.trim()==='中文' || !/[\u4e00-\u9fff]/.test(value)) return value
  const trimmed=value.trim()
  if(!trimmed) return value
  let translated=catalogue[trimmed]
  if(translated === undefined) {
    translated=trimmed.replace(/^未来 (\d+) 天$/, 'Next $1 days').replace(/^过去 (\d+) 天$/, 'Past $1 days')
    for(const [zh,en] of phrases) if(translated.includes(zh)) translated=translated.split(zh).join(en)
    translated=translated.replaceAll('：', ': ').replaceAll('；', '; ').replaceAll('，', ', ').replaceAll('。', '. ').replaceAll('／', ' / ').replaceAll('、', ', ')
  }
  return value.slice(0,value.indexOf(trimmed))+translated+value.slice(value.indexOf(trimmed)+trimmed.length)
}
// Translate the presentation tree without changing filter values, data or handlers.
// Child components with their own rendered content use Localized at their boundary.
function localize(children: ReactNode, language: Language): ReactNode {
  return Children.map(children, child => {
    if(typeof child==='string') return translate(child,language)
    if(!isValidElement<{children?:ReactNode; 'aria-label'?:string; title?:string; placeholder?:string}>(child)) return child
    const props=child.props
    const labels: Record<string,string>={}
    for(const key of ['aria-label','title','placeholder'] as const) if(typeof props[key]==='string') labels[key]=translate(props[key],language)
    return cloneElement(child,labels,props.children === undefined ? undefined : localize(props.children,language))
  })
}
export function Localized({children}:{children:ReactNode}) {
  const language=useLanguage()
  return <>{localize(children,language)}</>
}
