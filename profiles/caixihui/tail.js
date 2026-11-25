        /* CaiXiHui never sends browser-authored TeX to xelatex: the server
           regenerates the paper figure from this chart's own data and fields,
           then compiles that vetted source. It sends the PDF back inline as a
           blob URL, so nothing is filed under a run the studio does not own. */
        window.ZenVizTex = {
          async compile(tex, chart, progress) {
            progress('正在生成 LaTeX 并编译…')
            const res = await fetch('/api/visualize/latex-pdf', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(chart),
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok || !data.ok) throw new Error(data.error || '编译失败（HTTP ' + res.status + '）')
            progress('正在打开 PDF…')
            const binary = atob(data.pdf_base64 || '')
            const bytes = new Uint8Array(binary.length)
            for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
            const blob = new Blob([bytes], { type: 'application/pdf' })
            return { url: URL.createObjectURL(blob) }
          },
        }
