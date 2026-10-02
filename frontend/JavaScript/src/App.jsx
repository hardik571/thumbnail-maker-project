import { useState, useRef, useEffect } from 'react'

const API_BASE = "http://localhost:8000/api";

function App() {
  const [prompt, setPrompt] = useState("");
  const [numThumbnails, setNumThumbnails] = useState(1);
  const [headshotFile, setHeadshotFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [jobStatus, setJobStatus] = useState(""); // idle, uploading, generating, error
  const [activeJobId, setActiveJobId] = useState(null);
  
  // Results
  const [thumbnails, setThumbnails] = useState({});
  const fileInputRef = useRef(null);
  
  // Clean up ObjectURL
  useEffect(() => {
    return () => {
      if (previewUrl && previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setHeadshotFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const startJob = async (e) => {
    e.preventDefault();
    if (!headshotFile) {
      alert("Please upload a headshot photo first.");
      return;
    }
    
    setIsProcessing(true);
    setThumbnails({});
    setJobStatus("Uploading headshot...");

    try {
      // 1. Upload Headshot
      const formData = new FormData();
      formData.append("file", headshotFile);
      
      const uploadRes = await fetch(`${API_BASE}/upload-headshot`, {
        method: "POST",
        body: formData,
      });
      if (!uploadRes.ok) throw new Error("Failed to upload headshot");
      const { url: uploadedHeadshotUrl } = await uploadRes.json();

      // 2. Create Job
      setJobStatus("Starting generation job...");
      const jobRes = await fetch(`${API_BASE}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          num_thumbnails: numThumbnails,
          headshot_url: uploadedHeadshotUrl
        }),
      });
      if (!jobRes.ok) throw new Error("Failed to create job");
      const { job_id } = await jobRes.json();
      
      setActiveJobId(job_id);
      setJobStatus("Generating thumbnails models...");
      
      // 3. Connect to Event Source stream
      const sse = new EventSource(`${API_BASE}/jobs/${job_id}/stream`);
      
      sse.addEventListener("thumbnail_ready", (e) => {
        const data = JSON.parse(e.data);
        setThumbnails(prev => ({ ...prev, [data.thumbnail_id]: { ...data, status: 'uploaded' } }));
      });
      
      sse.addEventListener("thumbnail_failed", (e) => {
        const data = JSON.parse(e.data);
        setThumbnails(prev => ({ ...prev, [data.thumbnail_id]: { ...data, status: 'error' } }));
      });
      
      sse.addEventListener("job_completed", (e) => {
         // finished loading
         sse.close();
         setIsProcessing(false);
         setJobStatus("Job Completed!");
      });
      
      sse.addEventListener("error", (e) => {
        // SSE error or stream ended abruptly
        const data = e.data ? JSON.parse(e.data) : { error: "Unknown stream error" };
        if (data.error === "stream timeout") {
           console.log("Stream timed out.");
        }
        sse.close();
        setIsProcessing(false);
        setJobStatus(prev => prev === "Job Completed!" ? prev : "Error in generation process");
      });

    } catch (err) {
      console.error(err);
      setJobStatus(`Error: ${err.message}`);
      setIsProcessing(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>AI Thumbnail Maker</h1>
        <p>Turn your ideas into click-worthy YouTube thumbnails instantly.</p>
      </header>

      <div className="grid-layout">
        
        {/* LEFT COLUMN: Input Form */}
        <div className="glass-panel">
          <form onSubmit={startJob}>
            
            <div className="form-group">
              <label>Headshot Photo</label>
              <div 
                className="file-upload-box" 
                onClick={() => fileInputRef.current?.click()}
              >
                {previewUrl && <img src={previewUrl} alt="headshot preview" />}
                <div className="file-upload-content">
                  {headshotFile ? (
                    <p style={{ color: "#fff", fontWeight: "bold" }}>{headshotFile.name}</p>
                  ) : (
                    <>
                      <p>Click to upload your face</p>
                      <span style={{ fontSize: "2rem", display: "inline-block", marginTop: "1rem" }}>📷</span>
                    </>
                  )}
                </div>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  accept="image/*" 
                  style={{ display: "none" }} 
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="prompt">YouTube Video Idea / Title</label>
              <input 
                id="prompt"
                type="text" 
                value={prompt} 
                onChange={e => setPrompt(e.target.value)} 
                placeholder="e.g. 10 Secret Python Tips for 2026..."
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="count">Number of styles to generate (1-3)</label>
              <input 
                id="count"
                type="number" 
                min="1" 
                max="3" 
                value={numThumbnails} 
                onChange={e => setNumThumbnails(parseInt(e.target.value))} 
              />
            </div>

            <button type="submit" className="btn-primary" disabled={isProcessing}>
              {isProcessing ? jobStatus : 'Generate Thumbnails'}
            </button>
            
          </form>
        </div>

        {/* RIGHT COLUMN: Results Array */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          
          <div style={{ paddingBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1.5rem' }}>Your Thumbnails</h2>
            {isProcessing && <div className="status-badge generating pulse">{jobStatus}</div>}
            {!isProcessing && jobStatus === "Job Completed!" && <div className="status-badge uploaded">Completed</div>}
          </div>

          {!activeJobId && Object.keys(thumbnails).length === 0 && (
            <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)' }}>
              <p>Your generated thumbnails will appear here.</p>
            </div>
          )}

          <div className="thumbnails-grid">
            {Object.values(thumbnails).map(thumb => (
              <div key={thumb.thumbnail_id} className="thumbnail-card">
                <div className="thumbnail-card-image">
                  {thumb.status === 'uploaded' ? (
                     <img src={thumb.variants?.thumbnail || thumb.imagekit_url} alt={thumb.style_name} />
                  ) : thumb.status === 'error' ? (
                     <p style={{ color: 'var(--error)' }}>Failed generating</p>
                  ) : null}
                </div>
                <div className="thumbnail-card-info">
                  <div>
                    <div className="thumbnail-style">{thumb.style_name.replace('_', ' ')}</div>
                    <div className={`status-badge ${thumb.status}`}>{thumb.status}</div>
                  </div>
                  {thumb.status === 'uploaded' && (
                    <a href={thumb.imagekit_url} target="_blank" rel="noreferrer" className="download-btn">Open HD</a>
                  )}
                </div>
              </div>
            ))}
            
            {/* Show placeholders if we know how many are coming but they havent rendered yet */}
            {isProcessing && Array.from({ length: Math.max(0, numThumbnails - Object.keys(thumbnails).length) }).map((_, idx) => (
               <div key={`pending-${idx}`} className="thumbnail-card" style={{ opacity: 0.6 }}>
                  <div className="thumbnail-card-image pulse">
                    <div className="spinner"></div>
                  </div>
                  <div className="thumbnail-card-info">
                     <span style={{ color: 'var(--text-muted)' }}>Working on it...</span>
                  </div>
               </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  )
}

export default App
