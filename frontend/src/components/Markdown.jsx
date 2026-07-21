import { useMemo } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ gfm: true, breaks: false })

export default function Markdown({ source }) {
  const html = useMemo(() => {
    if (!source) return ''
    const raw = marked.parse(source)
    return DOMPurify.sanitize(raw, { ADD_ATTR: ['target', 'rel'] })
  }, [source])

  if (!source) {
    return <p className="muted">No model card provided.</p>
  }
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />
}
