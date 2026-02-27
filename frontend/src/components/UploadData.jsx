import React, { useState, useRef, useEffect } from 'react'
import { Upload, CheckCircle, AlertCircle, FileSpreadsheet, RefreshCw, Info } from 'lucide-react'
import { uploadData, getUploadStatus } from '../services/api'

export default function UploadData() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)   // { success, message, summary }
  const [error, setError] = useState(null)
  const [status, setStatus] = useState(null)   // current dataset status
  const inputRef = useRef(null)

  useEffect(() => {
    getUploadStatus()
      .then(setStatus)
      .catch(() => {})
  }, [])

  function handleFileChange(e) {
    const selected = e.target.files?.[0]
    if (selected) {
      setFile(selected)
      setResult(null)
      setError(null)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) {
      setFile(dropped)
      setResult(null)
      setError(null)
    }
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setProgress(0)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const data = await uploadData(formData, (evt) => {
        if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100))
      })
      setResult(data)
      // Refresh dataset status
      getUploadStatus().then(setStatus).catch(() => {})
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Upload failed. Please check the file format and try again.'
      setError(msg)
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-brand-text">Upload Sales Data</h2>
        <p className="text-sm text-brand-muted mt-1">
          Replace the current dataset with your own CSV or Excel file. All analytics will
          refresh immediately after a successful upload.
        </p>
      </div>

      {/* Current dataset status */}
      {status && (
        <div className="bg-brand-card border border-brand-border rounded-xl p-4 flex items-start gap-3">
          <Info size={16} className="text-blue-400 mt-0.5 shrink-0" />
          <div className="text-sm">
            <span className="text-brand-text font-medium">Current dataset: </span>
            <span className="text-brand-muted">
              {status.total_records.toLocaleString()} records &nbsp;·&nbsp;
              source: <span className={status.source === 'uploaded' ? 'text-green-400' : 'text-saffron-400'}>
                {status.source}
              </span>
              {status.last_upload && (
                <> &nbsp;·&nbsp; last upload: {new Date(status.last_upload).toLocaleString('en-IN')}</>
              )}
            </span>
          </div>
        </div>
      )}

      {/* Format guide */}
      <div className="bg-brand-card border border-brand-border rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-brand-text">Required File Format</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-brand-muted">
          <div>
            <p className="text-brand-text font-medium mb-1">Required columns</p>
            <ul className="space-y-0.5 list-disc list-inside">
              <li>invoice_date &nbsp;<span className="text-brand-muted">(YYYY-MM-DD)</span></li>
              <li>sku_code</li>
              <li>model_name</li>
              <li>variant</li>
              <li>colour</li>
            </ul>
          </div>
          <div>
            <p className="text-brand-text font-medium mb-1">Optional columns</p>
            <ul className="space-y-0.5 list-disc list-inside">
              <li>quantity_sold &nbsp;<span className="text-brand-muted">(default: 1)</span></li>
              <li>unit_price</li>
              <li>total_value &nbsp;<span className="text-brand-muted">(auto-calculated)</span></li>
              <li>location</li>
              <li>region</li>
            </ul>
          </div>
        </div>
        <p className="text-xs text-brand-muted">Supported formats: CSV, XLSX</p>
      </div>

      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
          ${file ? 'border-saffron-500 bg-saffron-500/5' : 'border-brand-border hover:border-saffron-500/50'}`}
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={handleFileChange}
        />
        <FileSpreadsheet size={36} className="mx-auto mb-3 text-brand-muted" />
        {file ? (
          <p className="text-sm font-medium text-saffron-400">{file.name}</p>
        ) : (
          <>
            <p className="text-sm text-brand-text">Drag &amp; drop a file here, or click to browse</p>
            <p className="text-xs text-brand-muted mt-1">CSV or Excel (.xlsx)</p>
          </>
        )}
      </div>

      {/* Progress bar */}
      {uploading && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-brand-muted">
            <span>Uploading…</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-brand-border rounded-full h-1.5">
            <div
              className="bg-saffron-500 h-1.5 rounded-full transition-all duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload button */}
      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-saffron-500 text-white text-sm font-medium
          hover:bg-saffron-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {uploading ? (
          <><RefreshCw size={15} className="animate-spin" /> Processing…</>
        ) : (
          <><Upload size={15} /> Upload &amp; Replace Data</>
        )}
      </button>

      {/* Success result */}
      {result?.success && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-green-400 font-medium">
            <CheckCircle size={18} />
            {result.message}
          </div>
          {result.summary && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <Stat label="Rows Imported" value={result.summary.total_rows.toLocaleString()} />
              <Stat label="Unique SKUs" value={result.summary.unique_skus} />
              <Stat label="Unique Models" value={result.summary.unique_models} />
              <Stat
                label="Date Range"
                value={`${result.summary.date_range.from} → ${result.summary.date_range.to}`}
              />
            </div>
          )}
          <p className="text-xs text-green-400/70">
            All analytics sections now reflect your uploaded data. Navigate to Dashboard,
            Sales Analytics, or Dispatch Planner to see the results.
          </p>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle size={18} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="bg-brand-bg rounded-lg p-3">
      <p className="text-xs text-brand-muted">{label}</p>
      <p className="text-sm font-semibold text-brand-text mt-0.5">{value}</p>
    </div>
  )
}
