import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const norm = (s) => s.toLowerCase().replace(/\s+/g, " ").trim();

export default function PdfViewer({ url, page, quote, title, onClose }) {
  const [doc, setDoc] = useState(null);
  const [n, setN] = useState(page);
  const [scale, setScale] = useState(1.3);
  const [boxes, setBoxes] = useState([]);
  const [err, setErr] = useState("");
  const canvasRef = useRef(null);
  const viewerRef = useRef(null);

  // Load the document whenever the cited PDF changes
  useEffect(() => {
    let dead = false;
    setDoc(null);
    setErr("");
    const task = pdfjs.getDocument(url);
    task.promise.then((d) => !dead && setDoc(d)).catch((e) => !dead && setErr(e.message));
    return () => {
      dead = true;
      task.destroy();
    };
  }, [url]);

  // Jump to the cited page when a citation is clicked
  useEffect(() => setN(page), [page, url, quote]);

  // Render the page and highlight the cited text
  useEffect(() => {
    if (!doc) return;
    let dead = false;
    let renderTask;
    (async () => {
      const pg = await doc.getPage(Math.min(Math.max(1, n), doc.numPages));
      const vp = pg.getViewport({ scale });
      const dpr = window.devicePixelRatio || 1;
      const c = canvasRef.current;
      c.width = vp.width * dpr;
      c.height = vp.height * dpr;
      c.style.width = vp.width + "px";
      c.style.height = vp.height + "px";
      renderTask = pg.render({ canvasContext: c.getContext("2d"), viewport: vp, transform: [dpr, 0, 0, dpr, 0, 0] });
      await renderTask.promise;
      if (dead) return;
      const found = [];
      if (quote && n === page) {
        const nq = norm(quote);
        const tc = await pg.getTextContent();
        for (const it of tc.items) {
          const t = norm(it.str);
          if (t.length < 4 || !nq.includes(t)) continue;
          const m = pdfjs.Util.transform(vp.transform, it.transform);
          const h = it.height * scale;
          found.push({ left: m[4], top: m[5] - h, width: it.width * scale, height: h * 1.15 });
        }
      }
      if (!dead) setBoxes(found);
    })().catch(() => {}); // cancelled renders throw; safe to ignore
    return () => {
      dead = true;
      renderTask && renderTask.cancel();
    };
  }, [doc, n, scale, quote, page]);

  useEffect(() => {
    if (boxes.length && viewerRef.current) {
      viewerRef.current.scrollTo({ top: Math.max(0, boxes[0].top - 120), behavior: "smooth" });
    }
  }, [boxes]);

  return (
    <>
      <div className="bar">
        <span className="bar-title" title={title}>{title}</span>
        <button onClick={() => setN(n - 1)} aria-label="Previous page">‹</button>
        <span className="pg">{doc ? `${n} / ${doc.numPages}` : "–"}</span>
        <button onClick={() => setN(n + 1)} aria-label="Next page">›</button>
        <button onClick={() => setScale((s) => Math.max(0.6, s - 0.2))} aria-label="Zoom out">−</button>
        <button onClick={() => setScale((s) => Math.min(3, s + 0.2))} aria-label="Zoom in">+</button>
        <button onClick={onClose} aria-label="Close PDF viewer">×</button>
      </div>
      <div className="viewer" ref={viewerRef}>
        {err && <p className="error">Could not load the PDF: {err}</p>}
        <div className="page" hidden={!doc}>
          <canvas ref={canvasRef} />
          {boxes.map((b, i) => (
            <div key={i} className="hl" style={b} />
          ))}
        </div>
        {!doc && !err && <p className="muted">Loading PDF…</p>}
      </div>
    </>
  );
}
