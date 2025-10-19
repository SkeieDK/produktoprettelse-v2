import React, { useState } from "react";

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");

  const runScraper = async () => {
    setLoading(true);
    setStatus("Summoning the archivists...");
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
                setLoading(false);
                return;
              } else if (js.status === 'failed') {
                setStatus('Job failed: ' + (js.message || 'unknown'));
                setLoading(false);
                return;
              } else {
                // still queued/running
                setStatus(`Scraper ${js.status}`);
                setTimeout(poll, 2000);
              }
            } else {
              setStatus('Failed to get job status');
              setLoading(false);
            }
          } catch (err) {
            setStatus('Error polling job status');
            setLoading(false);
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

  const fetchResults = async () => {
    setStatus("Retrieving scrolls...");
    try {
      const res = await fetch("/results");
      if (res.ok) {
        const data = await res.json();
        setResults(Array.isArray(data) ? data : []);
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
          <button className="btn-ghost" onClick={fetchResults}>Refresh</button>
          <button className="btn-cta" onClick={runScraper} disabled={loading}>{loading ? 'Working…' : 'Run Scraper'}</button>
        </div>
      </header>

      <main className="content">
        <div className="panel results-table-wrap">
          {results.length === 0 ? (
            <div className="empty-state panel" style={{padding:'3rem', textAlign:'center'}}>No results yet — click "Run Scraper" to populate the table.</div>
          ) : (
            <table className="results-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Product</th>
                  <th>Supplier info</th>
                  <th>Source</th>
                  <th>Images</th>
                  <th>Image sizes</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => {
                  const runSummary = r.run_summary || null;
                  const images = Array.isArray(r.images) ? r.images : (r.image_url ? [r.image_url] : []);
                  const imgCount = runSummary && typeof runSummary.images_found === 'number' ? runSummary.images_found : images.length;
                  const imageSizes = runSummary && runSummary.image_sizes ? runSummary.image_sizes : [];
                  const supplierSource = runSummary && runSummary.supplier_info_source ? runSummary.supplier_info_source : (r.supplier_info && r.supplier_info.includes('.pdf') ? 'pdf' : 'web');

                  let thumb = null;
                  if (images.length > 0) {
                    const first = images[0];
                    if (typeof first === 'string') thumb = first;
                    else if (first && typeof first === 'object') thumb = first.thumbnail || first.url || null;
                  } else if (r.image_url) thumb = r.image_url;

                  const supplierInfo = r.supplier_info || r.summary || '';

                  return (
                    <tr key={i} className="results-row">
                      <td className="td-thumb">
                        {thumb ? (
                          <img src={thumb} alt={r.product_number || 'thumb'} className="thumb-sm" onError={(e)=>{e.currentTarget.style.display='none'}} />
                        ) : (
                          <div className="thumb-placeholder" />
                        )}
                      </td>
                      <td className="td-product"><div className="product-number">{r.product_number || '—'}</div></td>
                      <td className="td-supplier">
                        <SupplierInfoSnippet text={supplierInfo} />
                      </td>
                      <td className="td-source">{supplierSource}</td>
                      <td className="td-images">{imgCount}</td>
                      <td className="td-sizes">
                        {imageSizes && imageSizes.length > 0 ? (
                          imageSizes.map((s, idx) => (
                            <div key={idx}>{Array.isArray(s) ? `${s[0]}x${s[1]} px` : s}</div>
                          ))
                        ) : (
                          <div style={{opacity:0.7}}>—</div>
                        )}
                      </td>
                      <td className="td-link">
                        {r.product_url ? <a href={r.product_url} target="_blank" rel="noopener noreferrer">Open</a> : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
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
