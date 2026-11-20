        /* 接收数据工作台“一键出图”投递的表格 */
        if (window.VizBridge) {
          window.VizBridge.onData(function (payload) {
            try {
              var csv = payload.csv
              if (!csv && Array.isArray(payload.headers)) {
                var lines = [payload.headers.join(',')]
                ;(payload.rows || []).forEach(function (r) { lines.push((r || []).join(',')) })
                csv = lines.join('\r\n')
              }
              state.data = parseTextData(String(csv || ''))
              normalizeDataSelection({ fillDefaults: true })
              renderDataTable()
              renderChart()
              setStatus('已接收 · ' + (payload.name || '数据表'))
            } catch (err) {
              console.error(err)
              setStatus('接收失败 · ' + (err.message || err), 'err')
            }
          })
        }

        /* 送复盘：把当前图表登记为一条复盘动态，交给 Hub 的 live 快照聚合后
         * 由 ZenReview 拉取。只写自己的 localStorage 键，不碰别的产品。 */
        function exportReview() {
          try {
            const KEY = 'zen.viz.review.v1'
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
            let list = []
            try { list = JSON.parse(localStorage.getItem(KEY) || '[]') } catch (e) { list = [] }
            if (!Array.isArray(list)) list = []
            list.push(entry)
            localStorage.setItem(KEY, JSON.stringify(list.slice(-50)))
            setStatus('已送复盘 · ' + entry.title)
          } catch (e) {
            reportError('送复盘失败', e, true)
          }
        }
        $('#save-review-btn').onclick = exportReview
