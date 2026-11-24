/* Paste-parsing for the studio's data panel.
 *
 * It lives in its own file so the parser can be run by a test: the studio app is one 14k-line IIFE
 * whose scope a harness cannot enter, and this is the one piece of it that turns untrusted text into
 * the table every chart is drawn from — worth measuring directly.
 *
 * Quoting follows RFC 4180. The lookup it replaced said `line.split(delim)`, so a quoted field
 * containing the delimiter was cut in half ("Beijing, China" became two cells) and every column
 * after it shifted by one: the pasted table loaded with each value under its neighbour's header and
 * nothing said so, because the grid still looked plausible. A doubled quote inside a quoted field is
 * one literal quote.
 */
(function (root) {
    'use strict';

    function hasClosingQuote(text, start) {
        for (var i = start + 1; i < text.length; i += 1) {
            if (text.charAt(i) !== '"') continue
            if (text.charAt(i + 1) === '"') i += 1
            else return true
        }
        return false
    }

    function delimiterOf(headerLine) {
        /* Delimiters inside quoted fields are data, not separators. Compare only
           the characters outside the first logical record, or `"a,b";"c,d"` is
           read as comma separated and every column shifts. A newline inside a
           quoted header belongs to that field; CRLF / lone CR outside it ends
           the record. Keep the original tab > comma > semicolon priority. */
        var outside = ''
        var quoted = false
        var line = String(headerLine || '')
        for (var i = 0; i < line.length; i += 1) {
            var ch = line.charAt(i)
            if (quoted) {
                if (ch === '"') {
                    if (line.charAt(i + 1) === '"') i += 1
                    else quoted = false
                }
                continue
            }
            if (ch === '\r' || ch === '\n') break
            if (ch === '"' && hasClosingQuote(line, i)) {
                quoted = true
                continue
            }
            outside += ch
        }
        if (outside.includes('\t')) return '\t'
        if (outside.includes(',')) return ','
        if (outside.includes(';')) return ';'
        if (/\s{2,}/.test(outside)) return 'whitespace'
        return ' '
    }

    /* Character state machine shared by textData and splitLine. Newlines are
       record separators only outside quotes; CRLF and lone CR inside quotes are
       kept verbatim as field data. Quoted fields keep their own leading/trailing
       whitespace, while ordinary fields retain the editor's historical
       trim-on-paste behaviour. */
    function parseRows(raw, delim) {
        var s = String(raw == null ? '' : raw).replace(/^\uFEFF/, '')
        var rows = []
        var row = []
        var field = ''
        var quoted = false
        var fieldWasQuoted = false
        var afterQuote = false

        function finishField() {
            row.push(fieldWasQuoted ? field : field.trim())
            field = ''
            fieldWasQuoted = false
            afterQuote = false
        }
        function finishRow() {
            finishField()
            if (row.some(function (cell) { return String(cell).trim() !== '' })) rows.push(row)
            row = []
        }

        for (var i = 0; i < s.length; i += 1) {
            var ch = s.charAt(i)
            if (quoted) {
                if (ch === '"') {
                    if (s.charAt(i + 1) === '"') {
                        field += '"'
                        i += 1
                    } else {
                        quoted = false
                        afterQuote = true
                    }
                } else {
                    field += ch
                }
                continue
            }

            if (ch === '\r' || ch === '\n') {
                finishRow()
                if (ch === '\r' && s.charAt(i + 1) === '\n') i += 1
                continue
            }
            if (afterQuote && /\s/.test(ch)) continue
            afterQuote = false

            if (delim === 'whitespace' && /\s/.test(ch)) {
                var end = i + 1
                while (end < s.length && /\s/.test(s.charAt(end))) end += 1
                if (end - i >= 2) {
                    finishField()
                    i = end - 1
                } else {
                    field += ch
                }
                continue
            }
            if (ch === '"' && field.trim() === '' && hasClosingQuote(s, i)) {
                field = ''
                quoted = true
                fieldWasQuoted = true
                continue
            }
            if (ch === delim) {
                finishField()
                continue
            }
            field += ch
        }
        finishRow()
        return rows
    }

    function splitLine(line, delim) {
        var rows = parseRows(line, delim)
        return rows.length ? rows[0] : ['']
    }

    function textData(raw) {
        var source = String(raw == null ? '' : raw)
            .replace(/^\uFEFF/, '')
            .replace(/^(?:[ \t]*(?:\r\n|\r|\n))+/, '')
        var records = parseRows(source, delimiterOf(source))
        if (!records.length) return { headers: [], rows: [] }
        var headers = records[0]
        var rows = records.slice(1)
        var max = headers.length
        rows.forEach(function (row) {
            if (row.length > max) max = row.length
        })
        while (headers.length < max) headers.push('列' + (headers.length + 1))
        rows = rows.map(function (row) {
            while (row.length < max) row.push('')
            return row
        })
        return { headers: headers, rows: rows }
    }

    root.ZenvizParse = { textData: textData, delimiterOf: delimiterOf, splitLine: splitLine }
})(typeof window !== 'undefined' ? window : globalThis)
