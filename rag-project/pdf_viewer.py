"""
Cited-source PDF viewer for the Streamlit app.

Only renders when the final answer cites at least one retrieved chunk.
The PDF is located through the Neo4j Document node linked to the cited chunk.
"""

import base64
import json
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from config import settings
from database.neo4j_client import neo4j_client

CITATION_RE = re.compile(r"\[([^\[\]]+)\]")


# ── Citation -> document lookup (Neo4j) ──────────────────────────────────────
def _doc_name_for_chunk(chunk_id: str):
    rows = neo4j_client.execute_query(
        "MATCH (c:Chunk {chunk_id: $cid})--(d:Document) RETURN d.name AS name LIMIT 1",
        {"cid": chunk_id},
    )
    return rows[0]["name"] if rows else None


@st.cache_data(show_spinner=False)
def _load_pdf(doc_name: str):
    """PDF bytes for a Document node: stored blob, then stored path, then DATA_DIR."""
    rows = neo4j_client.execute_query(
        "MATCH (d:Document {name: $n}) RETURN d.pdf_data AS blob, d.file_path AS path LIMIT 1",
        {"n": doc_name},
    )
    if rows:
        if rows[0].get("blob"):
            return bytes(rows[0]["blob"])
        p = rows[0].get("path")
        if p and Path(p).is_file():
            return Path(p).read_bytes()
    fallback = settings.DATA_DIR / f"{doc_name}.pdf"
    return fallback.read_bytes() if fallback.is_file() else None


def resolve_citations(answer: str, chunks) -> list[dict]:
    """Chunks the answer actually cites, e.g. [chunk_id], as [{chunk_id, doc, page}]."""
    by_id = {c.chunk_id: c for c in chunks}
    out, seen = [], set()
    for group in CITATION_RE.findall(answer or ""):
        for cid in (p.strip() for p in group.split(",")):
            if cid in by_id and cid not in seen:
                seen.add(cid)
                pages = by_id[cid].page_numbers or []
                doc = _doc_name_for_chunk(cid)
                if doc and pages:
                    out.append({"chunk_id": cid, "doc": doc, "page": int(min(pages))})
    return out


# ── Viewer ───────────────────────────────────────────────────────────────────
_HTML = """
<style>
 body{margin:0;font:14px system-ui,sans-serif;color:#1c2633}
 #bar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:6px 2px}
 button{border:1px solid #cbd3dc;background:#fff;border-radius:6px;padding:4px 10px;cursor:pointer}
 button.on{background:#2a56d6;color:#fff;border-color:#2a56d6}
 #v{height:__H__px;overflow:auto;background:#dfe4ea;text-align:center;padding:8px;border-radius:6px}
 canvas{box-shadow:0 1px 5px rgba(0,0,0,.25);background:#fff;max-width:100%}
</style>
<div id="bar"></div><div id="v"><canvas id="c"></canvas></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script>
pdfjsLib.GlobalWorkerOptions.workerSrc="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
const cited=__PAGES__, bar=document.getElementById("bar");
let doc,cur=cited[0];
function mk(t,fn,cls){const b=document.createElement("button");b.textContent=t;b.onclick=fn;if(cls)b.className=cls;bar.appendChild(b);return b}
function draw(){
  bar.innerHTML="";
  mk("‹",()=>go(cur-1)); 
  cited.forEach(p=>mk("p."+p,()=>go(p),p===cur?"on":""));
  mk("›",()=>go(cur+1));
  const s=document.createElement("span");s.textContent=" "+cur+" / "+doc.numPages;bar.appendChild(s);
}
async function go(n){
  cur=Math.min(Math.max(1,n),doc.numPages);draw();
  const pg=await doc.getPage(cur),w=document.getElementById("v").clientWidth-24;
  const base=pg.getViewport({scale:1}),vp=pg.getViewport({scale:Math.min(2,w/base.width)}),dpr=window.devicePixelRatio||1,c=document.getElementById("c");
  c.width=vp.width*dpr;c.height=vp.height*dpr;c.style.width=vp.width+"px";c.style.height=vp.height+"px";
  await pg.render({canvasContext:c.getContext("2d"),viewport:vp,transform:[dpr,0,0,dpr,0,0]}).promise;
  document.getElementById("v").scrollTop=0;
}
pdfjsLib.getDocument({data:atob("__B64__")}).promise.then(d=>{doc=d;go(cur)});
</script>
"""


def _render(pdf_bytes: bytes, pages: list[int], height: int = 680):
    html = (
        _HTML.replace("__H__", str(height - 60))
        .replace("__PAGES__", json.dumps(sorted(set(pages))))
        .replace("__B64__", base64.b64encode(pdf_bytes).decode())
    )
    components.html(html, height=height)


def show_sources(citations: list[dict]):
    """One collapsed expander per cited document; nothing is drawn if there are no citations."""
    docs: dict[str, list[int]] = {}
    for c in citations:
        docs.setdefault(c["doc"], []).append(c["page"])
    for doc, pages in docs.items():
        label = f"📄 Cited source: {doc} (p. {', '.join(map(str, sorted(set(pages))))})"
        with st.expander(label, expanded=False):
            data = _load_pdf(doc)
            if data:
                _render(data, pages)
            else:
                st.warning(f"Could not find the PDF for '{doc}'. Check the Document node's file_path or pdf_data.")
