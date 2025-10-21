import React, { useState } from "react";

function App() {
  const [results, setResults] = useState([]);
  const [processedProducts, setProcessedProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingCsv, setProcessingCsv] = useState(false);
  const [scraperRunning, setScraperRunning] = useState(false);
  const [scrapeProgress, setScrapeProgress] = useState({done:0,total:0});
  const [status, setStatus] = useState("");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [viewMode, setViewMode] = useState('processed'); // 'processed' | 'results'
  const [vendorSummary, setVendorSummary] = useState(null);

  const runScraper = async () => {
    setScraperRunning(true);
    setStatus("Summoning the archivists...");
    setScrapeProgress({done:0, total: processedProducts ? processedProducts.length : 0});
    try {
      const res = await fetch("/run-scraper", { method: "POST" });
      if (res.ok) {
        const body = await res.json();
        const jobId = body.job_id;
        setStatus("Job queued. Awaiting completion...");
        // poll job status until done or failed
        const poll = async () => {
          try {
            const sj = await fetch(`/jobs/${jobId}`);
            if (sj.ok) {
              const js = await sj.json();
              if (js.status === 'done') {
                setStatus('Job complete — fetching results');
                await fetchResults();
                setScraperRunning(false);
                setScrapeProgress({done: processedProducts ? processedProducts.length : 0, total: processedProducts ? processedProducts.length : 0});
                return;
              } else if (js.status === 'failed') {
                setStatus('Job failed: ' + (js.message || 'unknown'));
                setScraperRunning(false);
                return;
              } else {
                // still queued/running — update progress from results endpoint
                try {
                  const r = await fetch('/results');
                  if (r.ok) {
                    const d = await r.json();
                    const done = Array.isArray(d) ? d.length : 0;
                    const total = processedProducts ? processedProducts.length : 0;
                    setScrapeProgress({done, total});
                    setStatus(`Scraping ${done}/${total}`);
                  } else {
                    setStatus(`Scraper ${js.status}`);
                  }
                } catch (e) {
                  setStatus(`Scraper ${js.status}`);
                }
                setTimeout(poll, 2000);
              }
            } else {
              setStatus('Failed to get job status');
              setScraperRunning(false);
            }
          } catch (err) {
            setStatus('Error polling job status');
            setScraperRunning(false);
          }
        };
        setTimeout(poll, 1000);
      } else {
        setStatus("Failed to trigger scraper");
      }
    } catch (err) {
      setStatus("Error triggering scraper");
    }
    // loading cleared by poll when job completes or fails
  };

  const uploadCsv = async (file) => {
    if (!file) return;
    setStatus('Uploading CSV...');
    const fd = new FormData();
    fd.append('file', file, file.name);
    try {
      const res = await fetch('/upload-csv', { method: 'POST', body: fd });
      if (res.ok) {
        const js = await res.json();
        setStatus('CSV uploaded');
        setUploadedFile(js.filename);
      } else {
        const txt = await res.text();
        setStatus('Upload failed: ' + txt);
      }
    } catch (e) {
      setStatus('Network error during upload');
    }
  };

  const processUploadedCsv = async () => {
    setStatus('Processing CSV...');
    setProcessingCsv(true);
    try {
      const url = uploadedFile ? `/process-csv?filename=${encodeURIComponent(uploadedFile)}` : '/process-csv';
      const res = await fetch(url, { method: 'POST' });
      if (res.ok) {
        const js = await res.json();
        setStatus(`CSV processed (${js.rows} rows)`);
        // fetch processed products for preview
        const p = await fetch('/processed');
        if (p.ok) {
          const data = await p.json();
          const arr = Array.isArray(data) ? data : [];
          setProcessedProducts(arr);
          // derive vendor summary from first product if possible
          const vendor = arr && arr.length > 0 ? (arr[0].PrimaryVendorName || arr[0].BrandID || arr[0].PrimaryVendor || null) : null;
          setVendorSummary({ count: arr.length, vendor });
          setViewMode('processed');
          setStatus('Processed data loaded');
        } else {
          setStatus('Processed but no preview available');
        }
      } else {
        const txt = await res.text();
        setStatus('Processing failed: ' + txt);
      }
    } catch (e) {
      setStatus('Network error during processing');
    }
    finally {
      setProcessingCsv(false);
    }
  };

  const fetchResults = async () => {
    setStatus("Retrieving scrolls...");
    try {
      const res = await fetch("/results");
      if (res.ok) {
        const data = await res.json();
        setResults(Array.isArray(data) ? data : []);
        setViewMode('results');
        setStatus("Results retrieved");
      } else {
        setStatus("No results found");
      }
    } catch (err) {
      setStatus("Error fetching results");
    }
  };

  return (
    <div className="app-container">
      <header className="site-header">
        <div className="brand">
          <div className="logo" aria-hidden />
          <div>
            <div className="title">Produktoprettelse</div>
            <div className="tag">Supplier extraction dashboard</div>
          </div>
        </div>

        <div className="controls">
          <div className="status-pill">{status || 'Ready'}</div>
          {/* View toggle: Processed vs Scraper Results */}
          <div style={{display:'inline-block', marginRight:8}}>
            <button className={`btn-ghost ${viewMode==='processed' ? 'active' : ''}`} onClick={()=>setViewMode('processed')} style={{marginRight:6}} disabled={loading}>Processed</button>
            <button className={`btn-ghost ${viewMode==='results' ? 'active' : ''}`} onClick={()=>fetchResults()} disabled={loading}>Scraper results</button>
          </div>
          <button className="btn-ghost" onClick={fetchResults} disabled={loading}>Refresh</button>
          {/* Header Run Scraper button: primary only when processedProducts exist and not processing/scraping */}
          <button
            className={(processedProducts && processedProducts.length>0 && !processingCsv && !scraperRunning) ? 'btn-cta' : 'btn-ghost'}
            onClick={runScraper}
            disabled={scraperRunning || loading || !(processedProducts && processedProducts.length>0)}
          >
            {scraperRunning ? <><span className="btn-spinner"/> Scraping {scrapeProgress.done}/{scrapeProgress.total}</> : 'Run Scraper'}
          </button>
        </div>
      </header>

      {/* Banner when processed data is loaded but scraping not yet run */}
      {viewMode === 'processed' && processedProducts && processedProducts.length > 0 ? (
        <div style={{padding:'8px 20px', background:'#081221', color:'#8fe0c8', margin:'12px 20px', borderRadius:8}}>
          Processed {processedProducts.length} products — ready for scraping {vendorSummary && vendorSummary.vendor ? `at ${vendorSummary.vendor}` : ''}.
        </div>
      ) : null}

      <main className="content two-column">
        <section className="panel panel-left">
          <div className="section-header">
            <div>
              <h3>1 — CSV Sanitiser</h3>
              <div className="muted">Upload CSV and create a sanitised preview for scraping</div>
            </div>
            <div className="badge">Sanitiser</div>
          </div>

          <div style={{marginTop:12}}>
            <div style={{marginBottom:8}} className="muted">Upload a CSV file to sanitise</div>
            <input id="csvfile-2" type="file" accept=".csv" onChange={(e)=>{ if(e.target.files && e.target.files[0]) uploadCsv(e.target.files[0]) }} disabled={loading} />
            <div style={{marginTop:10}}>
              {uploadedFile ? (
                <button className={(processingCsv || loading) ? 'btn-ghost' : 'btn-cta'} onClick={processUploadedCsv} disabled={processingCsv || loading}>{processingCsv ? <span className="btn-spinner" /> : 'Process CSV'}</button>
              ) : (
                <div className="muted" style={{marginTop:10}}>No file uploaded</div>
              )}
            </div>
          </div>

          {processedProducts && processedProducts.length > 0 ? (
            <div style={{marginTop:16}}>
              <div className="info-banner">Processed {processedProducts.length} products — ready for scraping {vendorSummary && vendorSummary.vendor ? `at ${vendorSummary.vendor}` : ''}</div>
              <div style={{marginTop:12}} className="panel small">
                <table className="results-table small">
                  <thead>
                    <tr><th>Product</th><th>Supplier</th><th>Images</th></tr>
                  </thead>
                  <tbody>
                    {processedProducts.slice(0,8).map((r,i)=> (
                      <tr key={i}>
                        <td className="td-product"><div className="product-number">{r.PROD_NUM || r.PROD_NUM_old || r.PRD_NUM || '—'}</div></td>
                        <td className="td-supplier"><div className="summary">{r.PRIMARY_VENDOR_NAME || r.PrimaryVendorName || r.BrandID || ''}</div></td>
                        <td>{r.ImageURL ? 1 : 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="muted" style={{marginTop:8}}>Previewing first {Math.min(8, processedProducts.length)} rows</div>
              </div>
            </div>
          ) : null}
        </section>

        <section className="panel panel-right">
          <div className="section-header">
            <div>
              <h3>2 — Supplier Scraper</h3>
            </div>
            <div className="badge badge-accent">Scraper</div>
          </div>

          <div style={{marginTop:12}}>
            <div style={{marginBottom:8}} className="muted">The scraper will use the sanitised CSV saved on the server.</div>
            <div style={{display:'flex', gap:8, alignItems:'center'}}>
              <button className="btn-ghost" onClick={fetchResults} disabled={loading}>Refresh results</button>
              <button
                className={(processedProducts && processedProducts.length>0 && !processingCsv && !scraperRunning) ? 'btn-cta' : 'btn-ghost'}
                onClick={runScraper}
                disabled={scraperRunning || loading || !(processedProducts && processedProducts.length>0)}
              >
                {scraperRunning ? <><span className="btn-spinner"/> Scraping {scrapeProgress.done}/{scrapeProgress.total}</> : 'Run Scraper'}
              </button>
            </div>
          </div>

          <div style={{marginTop:16}}>
            {results && results.length > 0 ? (
              <div>
                <div className="muted">Latest scraped results (first 12)</div>
                <div className="panel small" style={{marginTop:8}}>
                  <table className="results-table small">
                    <thead><tr><th>Thumb</th><th>Product</th><th>Source</th><th>Images</th><th>Sizes</th></tr></thead>
                    <tbody>
                      {results.slice(0,12).map((r,i)=> {
                        const firstImg = (r.images && r.images.length && typeof r.images[0] === 'object') ? r.images[0] : null;
                        const imageCount = (r.images && r.images.length) || (r.image_url?1:0) || 0;
                        const sizes = r.run_summary && r.run_summary.image_sizes ? r.run_summary.image_sizes : [];
                        return (
                          <tr key={i}>
                            <td style={{width:80}}>{firstImg ? <img src={firstImg.thumbnail || firstImg.url} alt="thumb" style={{width:60,height:60,objectFit:'cover',borderRadius:6}} /> : null}</td>
                            <td className="product-number">{r.product_number || r.PROD_NUM || r.PROD_NUM_old || '—'}</td>
                            <td>{r.run_summary && r.run_summary.supplier_info_source ? r.run_summary.supplier_info_source : 'web'}</td>
                            <td>{imageCount}</td>
                            <td>{Array.isArray(sizes) ? sizes.map(s => Array.isArray(s) ? `${s[0]}x${s[1]}` : s).join(', ') : ''}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="muted">No scraped results yet. Run the scraper to populate this list.</div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function SupplierInfoSnippet({ text }){
  const [open, setOpen] = useState(false);
  const limit = 220;
  if(!text) return <div style={{opacity:0.7}}>No supplier info</div>;
  if(text.length <= limit) return <div className="summary">{text}</div>;
  return (
    <div>
      <div className="summary">{open ? text : text.slice(0, limit) + '...'}</div>
      <button className="linkish" onClick={()=>setOpen(!open)}>{open ? 'Show less' : 'Show more'}</button>
    </div>
  )
}

export default App;
