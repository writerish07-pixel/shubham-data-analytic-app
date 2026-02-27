import React, { useState, useRef } from 'react'
import { Upload, FileText, CheckCircle, XCircle, Download, AlertTriangle } from 'lucide-react'
import { uploadSalesData, getSalesUploadTemplateUrl } from '../services/api'

const REQUIRED_COLS = [
  { name: 'invoice_date', aliases: 'date, sale_date' },
  { name: 'sku_code',     aliases: 'sku' },
  { name: 'model_name',   aliases: 'model' },
  { name: 'variant',      aliases: '' },
  { name: 'colour',       aliases: 'color' },
]
const OPTIONAL_COLS = [
  { name: 'location',      note: '' },
  { name: 'region',        note: '' },
  { name: 'quantity_sold', note: 'defaults to 1 per row' },
  { name: 'unit_price',    note: 'defaults to 0' },
  { name: 'total_value',   note: 'auto-calculated if absent' },
]

export default function UploadData() {
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('idle') // idle | uploading | success | error
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const inputRef = useRef()

  const handleFile = (f) => {
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      setStatus('error')
      setErrorMsg('Only .csv, .xlsx, or .xls files are accepted.')
      return
    }
    setFile(f)
    setStatus('idle')
    setResult(null)
    setErrorMsg('')
    setProgress(0)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const onInputChange = (e) => handleFile(e.target.files[0])

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading')
    setProgress(0)
    setResult(null)
    setErrorMsg('')
    try {
      const data = await uploadSalesData(file, setProgress)
      setResult(data)
      setStatus('success')
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Upload failed.'
      setErrorMsg(detail)
      setStatus('error')
    }
  }

  const reset = () => {
    setFile(null)
    setStatus('idle')
    setResult(null)
    setErrorMsg('')
    setProgress(0)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-brand-text">Upload Sales Data</h2>
        <p className="text-sm text-brand-muted mt-1">
          Import your own CSV or Excel sales records into the analytics platform.
        </p>
      </div>

      {/* Template download */}
      <div className="bg-brand-card border border-brand-border rounded-xl p-4 flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-saffron-500/20 flex items-center justify-center shrink-0">
          <Download size={18} className="text-saffron-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-brand-text">Download Template</p>
          <p className="text-xs text-brand-muted">
            Use this CSV template so your file has the right column names.
          </p>
        </div>
        <a
          href={getSalesUploadTemplateUrl()}
          download="sales_upload_template.csv"
          className="shrink-0 text-xs bg-saffron-500/20 hover:bg-saffron-500/30 text-saffron-300 border border-saffron-500/30 px-4 py-2 rounded-lg transition"
        >
          Download CSV Template
        </a>
      </div>

      {/* Required columns */}
      <div className="bg-brand-card border border-brand-border rounded-xl p-4 space-y-3">
        <p className="text-sm font-semibold text-brand-text">Required Columns</p>
        <div className="flex flex-wrap gap-2">
          {REQUIRED_COLS.map(c => (
            <div key={c.name} className="flex flex-col items-start">
              <span className="text-xs bg-green-500/10 border border-green-500/30 text-green-400 px-2.5 py-1 rounded-md font-mono">
                {c.name}
              </span>
              {c.aliases && (
                <span className="text-[10px] text-brand-muted mt-0.5 px-1">also: {c.aliases}</span>
              )}
            </div>
          ))}
        </div>
        <p className="text-sm font-semibold text-brand-text pt-1">Optional Columns</p>
        <div className="flex flex-wrap gap-2">
          {OPTIONAL_COLS.map(c => (
            <div key={c.name} className="flex flex-col items-start">
              <span className="text-xs bg-blue-500/10 border border-blue-500/30 text-blue-400 px-2.5 py-1 rounded-md font-mono">
                {c.name}
              </span>
              {c.note && (
                <span className="text-[10px] text-brand-muted mt-0.5 px-1">{c.note}</span>
              )}
            </div>
          ))}
        </div>
        <p className="text-xs text-brand-muted pt-1">
          <span className="font-medium text-brand-text">invoice_date</span> format: <span className="font-mono">YYYY-MM-DD</span>
          &nbsp;·&nbsp;
          If <span className="font-mono">quantity_sold</span> is missing, each row counts as <span className="font-medium text-brand-text">1 unit sold</span>
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition
          ${dragging ? 'border-saffron-400 bg-saffron-500/10' : 'border-brand-border hover:border-saffron-500/50 hover:bg-brand-card/60'}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={onInputChange}
          className="hidden"
        />
        <Upload size={32} className="mx-auto mb-3 text-brand-muted" />
        {file ? (
          <div className="space-y-1">
            <p className="text-sm font-medium text-brand-text flex items-center justify-center gap-2">
              <FileText size={15} className="text-saffron-400" />
              {file.name}
            </p>
            <p className="text-xs text-brand-muted">{(file.size / 1024).toFixed(1)} KB · click to change file</p>
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium text-brand-text">Drag & drop your file here</p>
            <p className="text-xs text-brand-muted mt-1">or click to browse · CSV, XLSX, XLS supported</p>
          </div>
        )}
      </div>

      {/* Upload button */}
      {file && status !== 'uploading' && (
        <div className="flex gap-3">
          <button
            onClick={handleUpload}
            className="flex-1 bg-saffron-500 hover:bg-saffron-600 text-white text-sm font-semibold px-6 py-3 rounded-xl transition"
          >
            Upload & Import Data
          </button>
          <button
            onClick={reset}
            className="text-sm text-brand-muted hover:text-brand-text px-4 py-3 rounded-xl border border-brand-border transition"
          >
            Clear
          </button>
        </div>
      )}

      {/* Progress bar */}
      {status === 'uploading' && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-brand-muted">
            <span>Uploading…</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-brand-border rounded-full h-2">
            <div
              className="bg-saffron-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Success result */}
      {status === 'success' && result && (
        <div className="bg-brand-card border border-green-500/30 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-3">
            <CheckCircle size={20} className="text-green-400 shrink-0" />
            <p className="text-sm font-semibold text-green-400">Upload Successful</p>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-green-500/10 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-green-400">{result.rows_inserted}</p>
              <p className="text-xs text-brand-muted mt-0.5">Rows Imported</p>
            </div>
            <div className="bg-yellow-500/10 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-yellow-400">{result.rows_skipped}</p>
              <p className="text-xs text-brand-muted mt-0.5">Rows Skipped</p>
            </div>
            <div className="bg-brand-border/50 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-brand-text">{result.rows_inserted + result.rows_skipped}</p>
              <p className="text-xs text-brand-muted mt-0.5">Total Rows</p>
            </div>
          </div>
          {result.errors && result.errors.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-yellow-400 flex items-center gap-1.5">
                <AlertTriangle size={13} /> Row Errors (first {result.errors.length})
              </p>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {result.errors.map((e, i) => (
                  <p key={i} className="text-xs text-brand-muted font-mono bg-brand-border/30 rounded px-2 py-1">
                    Row {e.row}: {e.error}
                  </p>
                ))}
              </div>
            </div>
          )}
          <button onClick={reset} className="text-xs text-brand-muted hover:text-brand-text underline">
            Upload another file
          </button>
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="bg-brand-card border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
          <XCircle size={18} className="text-red-400 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-red-400">Upload Failed</p>
            <p className="text-xs text-brand-muted mt-1 break-words">{errorMsg}</p>
            <button onClick={reset} className="text-xs text-brand-muted hover:text-brand-text underline mt-2">
              Try again
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
