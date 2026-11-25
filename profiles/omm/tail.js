        function payloadCSV(payload) {
          if (!window.DataViz || typeof window.DataViz.toCSV !== 'function') {
            throw new Error('DataViz CSV 组件尚未加载')
          }
          if (!Array.isArray(payload.headers) || !Array.isArray(payload.rows)) {
            throw new Error('投递数据缺少 headers / rows')
          }
          return window.DataViz.toCSV({
            cols: payload.headers.map((name) => ({ name: String(name ?? '') })),
            rows: payload.rows,
          })
        }
        /* 接收数据工作台“一键出图”投递的表格 */
        function installDataReceiver() {
          if (!window.VizBridge) return
          window.VizBridge.onData(function (payload) {
            try {
              var csv = payloadCSV(payload)
              state.data = parseTextData(String(csv || ''))
              normalizeDataSelection({ fillDefaults: true })
              schedulePersist()
              renderDataTable()
              renderChart()
              setStatus('已接收 · ' + (payload.name || '数据表'))
            } catch (err) {
              console.error(err)
              setStatus('接收失败 · ' + (err.message || err), 'err')
            }
          })
        }
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', function () { setTimeout(installDataReceiver, 0) })
        } else installDataReceiver()

        /* 送复盘：桌面产品各自使用独立 origin，必须经共享 broker 写入 documents，
         * 不能把记录留在当前产品的 localStorage 里。 */
        function exportReview() {
          try {
            /* state.data is { headers: [...], rows: [...] }, not a bare array. */
            const data = state.data || {}
            const rows = Array.isArray(data.rows) ? data.rows : []
            const entry = {
              app: 'visualization',
              ts: new Date().toISOString(),
              title: String(state.title || '未命名图表'),
              chartType: String(state.type || 'chart'),
              rows: rows.length,
              cols: Array.isArray(data.headers) ? data.headers.length : 0,
            }
            const share = typeof window !== 'undefined' ? window.OMMShare : null
            if (share && typeof share.publishRecord === 'function') {
              setStatus('正在送复盘 · ' + entry.title, 'ok', false)
              return Promise.resolve(
                share.publishRecord(entry, {
                  channel: 'documents',
                  type: 'text/markdown',
                  format: 'omm.visualization.review',
                  title: '复盘 · ' + entry.title,
                  tags: ['复盘', '可视化'],
                }),
              ).then(
                function () {
                  setStatus('已送复盘 · ' + entry.title)
                  return true
                },
                function (err) {
                  reportError('送复盘失败', err, true)
                  return false
                },
              )
            }
            if (typeof window !== 'undefined' && window.OMMDesktop) {
              reportError('送复盘失败', new Error('共享服务不可用'), true)
              return false
            }
            // 仅在共享桥接与桌面桥都缺失的独立页面保留本地记录。
            const KEY = 'zen.viz.review.v1'
            let list = []
            try { list = JSON.parse(localStorage.getItem(KEY) || '[]') } catch (e) { list = [] }
            if (!Array.isArray(list)) list = []
            list.push(entry)
            localStorage.setItem(KEY, JSON.stringify(list.slice(-50)))
            setStatus('已送复盘 · ' + entry.title)
          } catch (e) {
            reportError('送复盘失败', e, true)
            return false
          }
        }
        $('#save-review-btn').onclick = exportReview

        /* OMM compiles through the existing ZENTEX local service. The studio
           only speaks the compile contract; the service owns the engine and
           the PDF it hands back. */
        window.ZenVizTex = {
          async compile(tex, chart, progress) {
            const bases = ['', 'http://127.0.0.1:8123']
            let last = null
            for (const base of bases) {
              try {
                progress(base ? '正在连接本地编译服务…' : '正在调用编译器…')
                const res = await fetch(base + '/api/compile', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ tex, engine: 'xelatex', passes: 1, mainfile: 'main.tex' }),
                })
                if (!res.ok) throw new Error('HTTP ' + res.status)
                const data = await res.json()
                if (!data.ok || !data.key) throw new Error(data.error || '编译服务未返回 PDF')
                progress('正在打开 PDF…')
                return { url: base + '/pdf?key=' + encodeURIComponent(data.key) }
              } catch (e) {
                last = e
              }
            }
            throw new Error(
              '未检测到本地 LaTeX 编译服务（请启动 server/latex-serve.py）：' +
                (last && last.message ? last.message : ''),
            )
          },
        }
