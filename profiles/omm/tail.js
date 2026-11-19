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
