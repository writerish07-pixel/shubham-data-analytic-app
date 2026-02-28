import React, { useState, useRef, useEffect } from 'react'
import { Upload, FileText, CheckCircle, XCircle, Download, AlertTriangle, Package, BarChart2, Trash2, Info } from 'lucide-react'
import {
  uploadSalesData, getSalesUploadTemplateUrl,
  uploadStockData, getStockTemplateUrl,
  getStockSummary, clearStockData,
} from '../services/api'

const SALES_REQUIRED = [
  { name: 'invoice_date', aliases: 'date, sale_date, bill_date, inv_date' },
  { name: 'sku_code',     aliases: 'sku, item_code, product_code, part_no' },
  { name: 'model_name',   aliases: 'model, product_name, item_name' },
  { name: 'variant',      aliases: 'type, grade  (auto-filled if missing)' },
  { name: 'colour',       aliases: 'color, shade  (auto-filled if missing)' },
]
const SALES_OPTIONAL = [
  { name: 'quantity_sold', note: 'qty / units / nos – defaults to 1' },
  { name: 'unit_price',    note: 'price / rate / mrp – defaults to 0' },
  { name: 'total_value',   note: 'amount / net_amount – auto-calculated' },
  { name: 'location',      note: 'city / dealer' },
  { name: 'region',        note: 'zone / state / territory' },
]

const STOCK_REQUIRED = [
  { name: 'sku_code',      aliases: 'sku, item_code, product_code, part_no, code' },
  { name: 'current_stock', aliases: 'stock, qty, quantity, available_qty, balance, on_hand, closing_stock' },
]
const STOCK_OPTIONAL = [
  { name: 'model_name', note: 'model / product_name / item_name' },
  { name: 'variant',    note: 'type / grade' },
  { name: 'colour',     note: 'color / shade' },
  { name: 'location',   note: 'city / warehouse / dealer' },
  { name: 'region',     note: 'zone / state / area' },
]

function UploadSection({ required, optional, templateUrl, uploadFn, onSuccess }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('idle')
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
    setFile(f); setStatus('idle'); setResult(null); setErrorMsg(''); setProgress(0)
  }

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading'); setProgress(0); setResult(null); setErrorMsg('')
    try {
      const data = await uploadFn(file, setProgress, true)
      setResult(data); setStatus('success')
      onSuccess && onSuccess()
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Upload failed.'
      setErrorMsg(detail); setStatus('error')
    }
  }

  const reset = () => {
    setFile(null); setStatus('idle'); setResult(null); setErrorMsg(''); setProgress(0)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="space-y-5">
      {/* Template download */}
      <div className="bg-brand-card border border-brand-border rounded-xl p-4 flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-saffron-500/20 flex items-center justify-center shrink-0">
          <Download size={18} className="text-saffron-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-brand-text">Download Template</p>
          <p className="text-xs text-brand-muted">Match your file columns to this template format.</p>
        </div>
        <a
          href={templateUrl}
          download
          className="shrink-0 text-xs bg-saffron-500/20 hover:bg-saffron-500/30 text-saffron-300 border border-saffron-500/30 px-4 py-2 rounded-lg transition"
        >
          Download CSV Template
        </a>
      </div>

      {/* Replace notice */}
      <div className="flex items-start gap-2 text-xs text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-xl px-4 py-3">
        <Info size={14} className="mt-0.5 shrink-0" />
        <span>
          <span className="font-semibold">Each upload replaces previous data.</span>{' '}
          The dashboard will show only your uploaded data — sample data is automatically removed.
        </span>
      </div>

      {/* Column guide */}
      <div className="bg-brand-card border border-brand-border rounded-xl p-4 space-y-3">
        <p className="text-sm font-semibold text-brand-text">Required Columns</p>
        <div className="flex flex-wrap gap-2">
          {required.map(c => (
            <div key={c.name} className="flex flex-col items-start">
              <span className="text-xs bg-green-500/10 border border-green-500/30 text-green-400 px-2.5 py-1 rounded-md font-mono">{c.name}</span>
              {c.aliases && <span className="text-[10px] text-brand-muted mt-0.5 px-1">also: {c.aliases}</span>}
            </div>
          ))}
        </div>
        <p className="text-sm font-semibold text-brand-text pt-1">Optional Columns</p>
        <div className="flex flex-wrap gap-2">
          {optional.map(c => (
            <div key={c.name} className="flex flex-col items-start">
              <span className="text-xs bg-blue-500/10 border border-blue-500/30 text-blue-400 px-2.5 py-1 rounded-md font-mono">{c.name}</span>
              {c.note && <span className="text-[10px] text-brand-muted mt-0.5 px-1">{c.note}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
        onClick={() => inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition
          ${dragging ? 'border-saffron-400 bg-saffron-500/10' : 'border-brand-border hover:border-saffron-500/50 hover:bg-brand-card/60'}`}
      >
        <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" onChange={e => handleFile(e.target.files[0])} className="hidden" />
        <Upload size={32} className="mx-auto mb-3 text-brand-muted" />
        {file ? (
          <div className="space-y-1">
            <p className="text-sm font-medium text-brand-text flex items-center justify-center gap-2">
              <FileText size={15} className="text-saffron-400" />{file.name}
            </p>
            <p className="text-xs text-brand-muted">{(file.size / 1024).toFixed(1)} KB · click to change</p>
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
          <button onClick={handleUpload} className="flex-1 bg-saffron-500 hover:bg-saffron-600 text-white text-sm font-semibold px-6 py-3 rounded-xl transition">
            Upload & Replace Data
          </button>
          <button onClick={reset} className="text-sm text-brand-muted hover:text-brand-text px-4 py-3 rounded-xl border border-brand-border transition">Clear</button>
        </div>
      )}

      {/* Progress */}
      {status === 'uploading' && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-brand-muted"><span>Uploading & processing…</span><span>{progress}%</span></div>
          <div className="w-full bg-brand-border rounded-full h-2">
            <div className="bg-saffron-500 h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Success */}
      {status === 'success' && result && (
        <div className="bg-brand-card border border-green-500/30 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-3">
            <CheckCircle size={20} className="text-green-400 shrink-0" />
            <p className="text-sm font-semibold text-green-400">Upload Successful — Dashboard now uses your data</p>
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
          {result.errors?.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-yellow-400 flex items-center gap-1.5"><AlertTriangle size={13} /> Row Errors (first {result.errors.length})</p>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {result.errors.map((e, i) => (
                  <p key={i} className="text-xs text-brand-muted font-mono bg-brand-border/30 rounded px-2 py-1">Row {e.row}: {e.error}</p>
                ))}
              </div>
            </div>
          )}
          <button onClick={reset} className="text-xs text-brand-muted hover:text-brand-text underline">Upload another file</button>
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="bg-brand-card border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
          <XCircle size={18} className="text-red-400 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-red-400">Upload Failed</p>
            <p className="text-xs text-brand-muted mt-1 break-words">{errorMsg}</p>
            <button onClick={reset} className="text-xs text-brand-muted hover:text-brand-text underline mt-2">Try again</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function UploadData() {
  const [tab, setTab] = useState('sales')
  const [stockSummary, setStockSummary] = useState(null)

  const loadStockSummary = () => {
    getStockSummary().then(setStockSummary).catch(() => {})
  }

  useEffect(() => { loadStockSummary() }, [])

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-brand-text">Upload Data</h2>
        <p className="text-sm text-brand-muted mt-1">
          Upload your sales history and current stock to power real analytics and dispatch planning.
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2 p-1 bg-brand-card border border-brand-border rounded-xl">
        <button
          onClick={() => setTab('sales')}
          className={`flex-1 flex items-center justify-center gap-2 text-sm py-2.5 rounded-lg font-medium transition ${
            tab === 'sales' ? 'bg-saffron-500/20 text-saffron-400 border border-saffron-500/30' : 'text-brand-muted hover:text-brand-text'
          }`}
        >
          <BarChart2 size={15} /> Sales Data
        </button>
        <button
          onClick={() => setTab('stock')}
          className={`flex-1 flex items-center justify-center gap-2 text-sm py-2.5 rounded-lg font-medium transition ${
            tab === 'stock' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'text-brand-muted hover:text-brand-text'
          }`}
        >
          <Package size={15} /> Current Stock Inventory
          {stockSummary?.has_stock_data && (
            <span className="ml-1 text-[10px] bg-green-500/20 text-green-400 border border-green-500/30 px-1.5 py-0.5 rounded-full">Loaded</span>
          )}
        </button>
      </div>

      {/* Sales Tab */}
      {tab === 'sales' && (
        <UploadSection
          required={SALES_REQUIRED}
          optional={SALES_OPTIONAL}
          templateUrl={getSalesUploadTemplateUrl()}
          uploadFn={uploadSalesData}
        />
      )}

      {/* Stock Tab */}
      {tab === 'stock' && (
        <div className="space-y-5">
          {/* Existing stock summary */}
          {stockSummary?.has_stock_data && (
            <div className="flex items-center justify-between bg-green-500/10 border border-green-500/30 rounded-xl px-4 py-3">
              <div className="flex items-center gap-3">
                <CheckCircle size={18} className="text-green-400" />
                <div>
                  <p className="text-sm font-semibold text-green-400">Stock Data Active</p>
                  <p className="text-xs text-brand-muted">
                    {stockSummary.total_skus} SKUs · {stockSummary.total_units?.toLocaleString('en-IN')} units on hand
                  </p>
                </div>
              </div>
              <button
                onClick={() => clearStockData().then(loadStockSummary)}
                className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 border border-red-500/30 px-3 py-1.5 rounded-lg transition"
              >
                <Trash2 size={12} /> Clear
              </button>
            </div>
          )}

          <UploadSection
            required={STOCK_REQUIRED}
            optional={STOCK_OPTIONAL}
            templateUrl={getStockTemplateUrl()}
            uploadFn={uploadStockData}
            onSuccess={loadStockSummary}
          />

          {/* Explanation */}
          <div className="bg-brand-card border border-brand-border rounded-xl p-4 space-y-2">
            <p className="text-sm font-semibold text-brand-text flex items-center gap-2">
              <Info size={14} className="text-saffron-400" /> How stock data is used
            </p>
            <ul className="text-xs text-brand-muted space-y-1.5 list-disc list-inside">
              <li>The <span className="text-brand-text font-medium">Dispatch Planner</span> subtracts your current stock from the forecast — so you only order what is actually needed.</li>
              <li>SKUs where existing stock covers the forecast will show <span className="text-green-400 font-medium">Overstock</span> or zero dispatch.</li>
              <li>Upload a fresh stock file any time to refresh the plan.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
