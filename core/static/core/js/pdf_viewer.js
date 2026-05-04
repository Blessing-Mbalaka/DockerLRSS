/**
 * Inline PDF viewer with role-isolated annotations.
 *
 * Usage:
 *   openPdfViewer(url, title, submissionId)
 *
 * When submissionId is provided, annotations are loaded from the role-aware API:
 * users can add annotations, select their own annotations, and delete only the
 * selected annotations they own. Other users' annotations remain visible but
 * locked.
 */

(function (global) {
  'use strict';

  const PDFJS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
  const PDFJS_WORKER = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  const PDFLIB_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js';

  const FALLBACK_COLORS = {
    assessor_marker: '#FF6B6B',
    internal_mod: '#4ECDC4',
    external_mod: '#FFE66D',
  };

  let pdfDoc = null;
  let currentPage = 1;
  let totalPages = 0;
  let scale = 1.3;
  let currentTool = null;
  let annotations = [];
  let selectedIds = new Set();
  let currentUrl = '';
  let currentSubmissionId = null;
  let modalInjected = false;
  let pendingComment = null;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + '=')) {
        return decodeURIComponent(trimmed.substring(name.length + 1));
      }
    }
    return '';
  }

  function apiUrl(path) {
    return `${window.location.origin}${path}`;
  }

  function injectModal() {
    if (modalInjected) return;
    modalInjected = true;

    const html = `
<div id="pdfViewerModal" style="display:none; position:fixed; inset:0; z-index:9999; background:rgba(0,0,0,.65); overflow:auto;">
  <div style="background:#fff; margin:20px auto; border-radius:8px; width:calc(100% - 40px); max-width:1120px; box-shadow:0 8px 32px rgba(0,0,0,.4); overflow:hidden;">
    <div style="display:flex; align-items:center; justify-content:space-between; background:#3d0b56; color:#fff; padding:10px 16px;">
      <span id="pdfViewerTitle" style="font-weight:600; font-size:15px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; max-width:60%;"></span>
      <div style="display:flex; gap:8px; align-items:center;">
        <a id="pdfDownloadLink" href="#" download style="color:#fff; font-size:13px; text-decoration:none;">Download</a>
        <button onclick="closePdfViewer()" style="background:none; border:none; color:#fff; font-size:20px; cursor:pointer; line-height:1;">x</button>
      </div>
    </div>

    <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px; padding:8px 12px; background:#f3edf7; border-bottom:1px solid #ddd;">
      <button onclick="pdfPrevPage()" class="pdf-tool-btn" title="Previous page">&lt;</button>
      <span style="font-size:13px;">Page <span id="pdfPageNum">1</span> / <span id="pdfPageCount">?</span></span>
      <button onclick="pdfNextPage()" class="pdf-tool-btn" title="Next page">&gt;</button>

      <span class="pdf-separator"></span>
      <button onclick="pdfZoomOut()" class="pdf-tool-btn" title="Zoom out">-</button>
      <button onclick="pdfZoomIn()" class="pdf-tool-btn" title="Zoom in">+</button>

      <span class="pdf-separator"></span>
      <button id="toolTick" onclick="setTool('tick')" class="pdf-tool-btn ann-btn" title="Add tick">Tick</button>
      <button id="toolCross" onclick="setTool('cross')" class="pdf-tool-btn ann-btn" title="Add cross">Cross</button>
      <button id="toolComment" onclick="setTool('comment')" class="pdf-tool-btn ann-btn" title="Add comment">Comment</button>
      <button id="toolSelect" onclick="setTool('select')" class="pdf-tool-btn ann-btn" title="Select your annotations">Select</button>
      <button onclick="deleteSelectedAnnotations()" class="pdf-tool-btn" style="color:#b00020;" title="Delete selected annotations you own">Delete Selected</button>

      <span class="pdf-separator"></span>
      <button onclick="savePdfWithAnnotations()" class="pdf-tool-btn" style="background:#3d0b56; color:#fff; font-weight:600;" title="Download PDF with visible annotations">Save PDF</button>
      <span id="pdfSaveStatus" style="font-size:12px; color:#555;"></span>
    </div>

    <div id="annotationNotice" style="display:none; padding:7px 12px; background:#fff8e1; color:#5f4500; border-bottom:1px solid #ead88a; font-size:12px;"></div>

    <div style="display:grid; grid-template-columns:minmax(0,1fr) 260px; min-height:300px;">
      <div style="overflow:auto; background:#888; padding:12px; text-align:center; position:relative;">
        <div id="pdfCanvasWrapper" style="display:inline-block; position:relative; cursor:crosshair;">
          <canvas id="pdfCanvas" style="display:block; box-shadow:0 2px 8px rgba(0,0,0,.3);"></canvas>
          <canvas id="annCanvas" style="position:absolute; top:0; left:0; pointer-events:none;"></canvas>
          <div id="pdfClickLayer" style="position:absolute; top:0; left:0; width:100%; height:100%;"></div>
        </div>
      </div>
      <aside style="background:#fafafa; border-left:1px solid #ddd; padding:10px; overflow:auto; max-height:78vh;">
        <div style="font-weight:700; font-size:13px; margin-bottom:8px;">Annotations</div>
        <div class="role-key">
          <span><i style="background:#FF6B6B;"></i> Assessor Marker</span>
          <span><i style="background:#4ECDC4;"></i> Internal Moderator</span>
          <span><i style="background:#FFE66D;"></i> External Moderator</span>
        </div>
        <div id="annotationList" style="display:flex; flex-direction:column; gap:6px;"></div>
      </aside>
    </div>
  </div>
</div>

<div id="commentPopup" style="display:none; position:fixed; z-index:10000; background:#fff; border:2px solid #3d0b56; border-radius:6px; padding:10px; box-shadow:0 4px 16px rgba(0,0,0,.3); min-width:220px;">
  <div style="font-size:13px; font-weight:600; margin-bottom:6px;">Add Comment</div>
  <textarea id="commentText" rows="3" style="width:100%; font-size:13px; border:1px solid #ccc; border-radius:4px; padding:4px;" placeholder="Type comment..."></textarea>
  <div style="display:flex; gap:6px; margin-top:6px; justify-content:flex-end;">
    <button onclick="cancelComment()" style="font-size:12px; padding:3px 10px; border:1px solid #ccc; border-radius:4px; cursor:pointer;">Cancel</button>
    <button onclick="confirmComment()" style="font-size:12px; padding:3px 10px; background:#3d0b56; color:#fff; border:none; border-radius:4px; cursor:pointer;">Add</button>
  </div>
</div>

<style>
  .pdf-tool-btn { padding:4px 10px; font-size:13px; border-radius:4px; border:1px solid #bbb; cursor:pointer; background:#fff; transition:background .15s; }
  .pdf-tool-btn:hover { background:#e8d5f5; }
  .ann-btn.active { background:#3d0b56 !important; color:#fff !important; border-color:#3d0b56; }
  .pdf-separator { width:1px; height:24px; background:#ccc; margin:0 4px; }
  .role-key { display:flex; flex-direction:column; gap:4px; font-size:11px; color:#555; margin-bottom:10px; }
  .role-key i { display:inline-block; width:10px; height:10px; border-radius:50%; border:1px solid rgba(0,0,0,.2); margin-right:5px; vertical-align:-1px; }
  .annotation-item { border:1px solid #ddd; border-left-width:4px; border-radius:6px; background:#fff; padding:7px; font-size:12px; cursor:pointer; }
  .annotation-item.selected { outline:2px solid #3d0b56; }
  .annotation-item.locked { opacity:.75; cursor:default; }
  .annotation-item button { border:1px solid #d0a0a0; color:#a00018; background:#fff; border-radius:4px; font-size:11px; padding:2px 6px; cursor:pointer; }
  @media (max-width:900px) {
    #pdfViewerModal [style*="grid-template-columns"] { display:block !important; }
    #pdfViewerModal aside { max-height:180px !important; border-left:none !important; border-top:1px solid #ddd; }
  }
</style>`;

    document.body.insertAdjacentHTML('beforeend', html);
    document.getElementById('pdfClickLayer').addEventListener('click', onCanvasClick);
  }

  function showNotice(message) {
    const notice = document.getElementById('annotationNotice');
    notice.textContent = message;
    notice.style.display = message ? 'block' : 'none';
  }

  async function loadAnnotations() {
    if (!currentSubmissionId) {
      showNotice('Annotation management is available from marker and moderator submission views.');
      renderAnnotationList();
      return;
    }

    try {
      const response = await fetch(apiUrl(`/api/annotations/${currentSubmissionId}/list/`), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await response.json();
      if (!data.success) throw new Error(data.message || 'Unable to load annotations');
      annotations = data.annotations || [];
      showNotice('');
    } catch (error) {
      console.error('Annotation load error:', error);
      showNotice('Annotations could not be loaded. You can still view the PDF.');
      annotations = [];
    }
    selectedIds.clear();
    drawAnnotations();
    renderAnnotationList();
  }

  async function createAnnotation(annotation) {
    if (!currentSubmissionId) {
      annotations.push({ ...annotation, id: `local-${Date.now()}`, colour: '#3d0b56', is_mine: true, owner_name: 'You' });
      drawAnnotations();
      renderAnnotationList();
      return;
    }

    const response = await fetch(apiUrl(`/api/annotations/${currentSubmissionId}/add/`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(annotation),
    });
    const data = await response.json();
    if (!data.success) throw new Error(data.message || 'Unable to add annotation');
    annotations.push(data.annotation);
    drawAnnotations();
    renderAnnotationList();
  }

  function normalizeAnnotation(raw) {
    return {
      type: raw.type,
      page: raw.page,
      x: raw.x,
      y: raw.y,
      text: raw.text || '',
    };
  }

  async function onCanvasClick(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (currentTool === 'select') {
      const hit = findAnnotationAt(x, y);
      if (hit && hit.is_mine) toggleSelected(hit.id);
      return;
    }

    if (!currentTool) return;

    const annotation = normalizeAnnotation({
      type: currentTool,
      page: currentPage,
      x: x / rect.width,
      y: y / rect.height,
      text: '',
    });

    if (currentTool === 'comment') {
      pendingComment = annotation;
      showCommentPopup(e.clientX, e.clientY);
      return;
    }

    try {
      await createAnnotation(annotation);
    } catch (error) {
      console.error('Annotation create error:', error);
      alert(error.message);
    }
  }

  function showCommentPopup(cx, cy) {
    const popup = document.getElementById('commentPopup');
    document.getElementById('commentText').value = '';
    popup.style.left = Math.min(cx, window.innerWidth - 250) + 'px';
    popup.style.top = Math.min(cy, window.innerHeight - 140) + 'px';
    popup.style.display = 'block';
    document.getElementById('commentText').focus();
  }

  global.cancelComment = function () {
    document.getElementById('commentPopup').style.display = 'none';
    pendingComment = null;
  };

  global.confirmComment = async function () {
    const text = document.getElementById('commentText').value.trim();
    if (text && pendingComment) {
      try {
        await createAnnotation({ ...pendingComment, text });
      } catch (error) {
        console.error('Annotation create error:', error);
        alert(error.message);
      }
    }
    document.getElementById('commentPopup').style.display = 'none';
    pendingComment = null;
  };

  function annotationColor(annotation) {
    return annotation.colour || FALLBACK_COLORS[annotation.role] || '#3d0b56';
  }

  function canvasPoint(annotation) {
    const canvas = document.getElementById('annCanvas');
    return {
      x: annotation.x * canvas.width,
      y: annotation.y * canvas.height,
    };
  }

  function findAnnotationAt(x, y) {
    const pageAnnotations = annotations.filter(a => a.page === currentPage);
    for (let i = pageAnnotations.length - 1; i >= 0; i--) {
      const annotation = pageAnnotations[i];
      const point = canvasPoint(annotation);
      const distance = Math.hypot(point.x - x, point.y - y);
      if (distance <= (annotation.type === 'comment' ? 28 : 20)) {
        return annotation;
      }
    }
    return null;
  }

  function toggleSelected(id) {
    if (selectedIds.has(id)) {
      selectedIds.delete(id);
    } else {
      selectedIds.add(id);
    }
    drawAnnotations();
    renderAnnotationList();
  }

  function drawAnnotations() {
    const ac = document.getElementById('annCanvas');
    const pc = document.getElementById('pdfCanvas');
    if (!ac || !pc) return;
    ac.width = pc.width;
    ac.height = pc.height;

    const ctx = ac.getContext('2d');
    ctx.clearRect(0, 0, ac.width, ac.height);

    annotations
      .filter(a => a.page === currentPage)
      .forEach(a => {
        const point = canvasPoint(a);
        const color = annotationColor(a);

        ctx.save();
        ctx.fillStyle = color;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        if (a.type === 'tick') {
          ctx.font = 'bold 30px Arial';
          ctx.fillText('✓', point.x - 10, point.y + 10);
        } else if (a.type === 'cross') {
          ctx.font = 'bold 30px Arial';
          ctx.fillText('×', point.x - 10, point.y + 10);
        } else if (a.type === 'comment') {
          ctx.font = '12px Arial';
          const text = a.text || '';
          const tw = Math.min(ctx.measureText(text).width + 16, ac.width - 12);
          const th = 24;
          const bx = Math.min(point.x + 6, ac.width - tw - 6);
          const by = Math.max(point.y - th - 6, 6);
          ctx.globalAlpha = 0.92;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.roundRect(bx, by, tw, th, 4);
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.fillStyle = '#222';
          ctx.fillText(text, bx + 8, by + 16);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
          ctx.fill();
        }

        if (selectedIds.has(a.id)) {
          ctx.strokeStyle = '#3d0b56';
          ctx.setLineDash([4, 3]);
          ctx.strokeRect(point.x - 18, point.y - 18, 36, 36);
        }
        ctx.restore();
      });
  }

  function renderAnnotationList() {
    const list = document.getElementById('annotationList');
    if (!list) return;

    const visible = annotations.filter(a => a.page === currentPage);
    if (!visible.length) {
      list.innerHTML = '<div style="font-size:12px; color:#777;">No annotations on this page.</div>';
      return;
    }

    list.innerHTML = '';
    visible.forEach(annotation => {
      const item = document.createElement('div');
      item.className = `annotation-item${selectedIds.has(annotation.id) ? ' selected' : ''}${annotation.is_mine ? '' : ' locked'}`;
      item.style.borderLeftColor = annotationColor(annotation);
      item.title = annotation.is_mine ? 'Click to select' : 'Created by another user';

      const label = annotation.type === 'comment' ? (annotation.text || 'Comment') : annotation.type;
      item.innerHTML = `
        <div style="display:flex; justify-content:space-between; gap:6px; align-items:start;">
          <div>
            <strong>${escapeHtml(label)}</strong>
            <div style="color:#666;">${escapeHtml(annotation.owner_name || 'Unknown')}</div>
          </div>
          ${annotation.is_mine ? '<button type="button">Delete</button>' : '<span style="font-size:11px; color:#777;">Locked</span>'}
        </div>`;

      if (annotation.is_mine) {
        item.addEventListener('click', () => toggleSelected(annotation.id));
        item.querySelector('button').addEventListener('click', async (event) => {
          event.stopPropagation();
          selectedIds = new Set([annotation.id]);
          await global.deleteSelectedAnnotations();
        });
      }
      list.appendChild(item);
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function renderPage(num) {
    if (!pdfDoc) return;
    const page = await pdfDoc.getPage(num);
    const viewport = page.getViewport({ scale });
    const canvas = document.getElementById('pdfCanvas');
    const ctx = canvas.getContext('2d');
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    const ac = document.getElementById('annCanvas');
    ac.width = viewport.width;
    ac.height = viewport.height;

    await page.render({ canvasContext: ctx, viewport }).promise;
    document.getElementById('pdfPageNum').textContent = num;
    drawAnnotations();
    renderAnnotationList();
  }

  global.openPdfViewer = async function (url, title, submissionId) {
    injectModal();
    currentUrl = url;
    currentSubmissionId = submissionId || null;
    annotations = [];
    selectedIds.clear();
    currentPage = 1;
    currentTool = null;
    document.querySelectorAll('.ann-btn').forEach(b => b.classList.remove('active'));

    document.getElementById('pdfViewerTitle').textContent = title || 'PDF Viewer';
    document.getElementById('pdfViewerModal').style.display = 'block';
    document.getElementById('pdfSaveStatus').textContent = '';
    document.getElementById('annotationList').innerHTML = '<div style="font-size:12px; color:#777;">Loading...</div>';

    const dlLink = document.getElementById('pdfDownloadLink');
    dlLink.href = url;
    dlLink.download = (title || 'document') + '.pdf';

    document.getElementById('pdfPageNum').textContent = '...';
    document.getElementById('pdfPageCount').textContent = '...';

    try {
      await loadScript(PDFJS_URL);
      await loadScript(PDFLIB_URL);

      const pdfjsLib = window['pdfjs-dist/build/pdf'];
      pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;

      pdfDoc = await pdfjsLib.getDocument(url).promise;
      totalPages = pdfDoc.numPages;
      document.getElementById('pdfPageCount').textContent = totalPages;
      await renderPage(1);
      await loadAnnotations();
    } catch (error) {
      console.error('PDF Viewer error:', error);
      document.getElementById('pdfPageNum').textContent = 'Error';
    }
  };

  global.closePdfViewer = function () {
    document.getElementById('pdfViewerModal').style.display = 'none';
    document.getElementById('commentPopup').style.display = 'none';
    pdfDoc = null;
    annotations = [];
    selectedIds.clear();
    currentTool = null;
    currentSubmissionId = null;
    document.querySelectorAll('.ann-btn').forEach(b => b.classList.remove('active'));
  };

  global.pdfPrevPage = async function () {
    if (!pdfDoc || currentPage <= 1) return;
    currentPage--;
    selectedIds.clear();
    await renderPage(currentPage);
  };

  global.pdfNextPage = async function () {
    if (!pdfDoc || currentPage >= totalPages) return;
    currentPage++;
    selectedIds.clear();
    await renderPage(currentPage);
  };

  global.pdfZoomIn = async function () {
    scale = Math.min(scale + 0.2, 3.0);
    await renderPage(currentPage);
  };

  global.pdfZoomOut = async function () {
    scale = Math.max(scale - 0.2, 0.5);
    await renderPage(currentPage);
  };

  global.setTool = function (tool) {
    currentTool = currentTool === tool ? null : tool;
    document.querySelectorAll('.ann-btn').forEach(b => b.classList.remove('active'));
    if (currentTool) {
      document.getElementById('tool' + tool.charAt(0).toUpperCase() + tool.slice(1)).classList.add('active');
    }
  };

  global.deleteSelectedAnnotations = async function () {
    const ids = Array.from(selectedIds).filter(id => !String(id).startsWith('local-'));
    if (!ids.length) {
      alert('Select one or more of your annotations first.');
      return;
    }

    try {
      const response = await fetch(apiUrl('/api/annotations/delete-bulk/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ ids }),
      });
      const data = await response.json();
      if (!data.success) throw new Error(data.message || 'Unable to delete annotations');

      const deleted = new Set(ids);
      annotations = annotations.filter(a => !deleted.has(a.id));
      selectedIds.clear();
      drawAnnotations();
      renderAnnotationList();
      document.getElementById('pdfSaveStatus').textContent = data.message || 'Deleted.';
      setTimeout(() => { document.getElementById('pdfSaveStatus').textContent = ''; }, 3000);
    } catch (error) {
      console.error('Annotation delete error:', error);
      alert(error.message);
    }
  };

  global.savePdfWithAnnotations = async function () {
    const status = document.getElementById('pdfSaveStatus');
    status.textContent = 'Saving...';

    try {
      const { PDFDocument, rgb, StandardFonts } = window.PDFLib;
      const response = await fetch(currentUrl);
      const bytes = await response.arrayBuffer();
      const pdfLibDoc = await PDFDocument.load(bytes);
      const helvetica = await pdfLibDoc.embedFont(StandardFonts.HelveticaBold);
      const pages = pdfLibDoc.getPages();

      annotations.forEach(a => {
        const pageObj = pages[a.page - 1];
        if (!pageObj) return;

        const { width: pageWidth, height: pageHeight } = pageObj.getSize();
        const pdfX = a.x * pageWidth;
        const pdfY = pageHeight - (a.y * pageHeight);
        const color = hexToRgb(annotationColor(a));

        if (a.type === 'tick') {
          pageObj.drawText('V', { x: pdfX - 6, y: pdfY - 6, size: 20, font: helvetica, color });
        } else if (a.type === 'cross') {
          pageObj.drawText('X', { x: pdfX - 6, y: pdfY - 6, size: 20, font: helvetica, color });
        } else if (a.type === 'comment') {
          const safeText = (a.text || '').replace(/[^\x20-\x7E]/g, '?');
          const fontSize = 9;
          const textWidth = helvetica.widthOfTextAtSize(safeText, fontSize);
          const pad = 4;
          const boxW = textWidth + pad * 2;
          const boxH = fontSize + pad * 2;

          pageObj.drawRectangle({
            x: pdfX + 6,
            y: pdfY - boxH,
            width: boxW,
            height: boxH,
            color,
            borderColor: rgb(0.2, 0.2, 0.2),
            borderWidth: 1,
          });
          pageObj.drawCircle({ x: pdfX, y: pdfY, size: 3, color });
          pageObj.drawText(safeText, {
            x: pdfX + 6 + pad,
            y: pdfY - boxH + pad,
            size: fontSize,
            font: helvetica,
            color: rgb(0.05, 0.05, 0.05),
          });
        }
      });

      const savedBytes = await pdfLibDoc.save();
      const blob = new Blob([savedBytes], { type: 'application/pdf' });
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = (document.getElementById('pdfViewerTitle').textContent || 'annotated') + '_annotated.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);

      status.textContent = 'Saved.';
      setTimeout(() => { status.textContent = ''; }, 3000);
    } catch (error) {
      console.error('Save error:', error);
      status.textContent = 'Save failed.';
    }
  };

  function hexToRgb(hex) {
    const clean = String(hex || '#000000').replace('#', '');
    const value = parseInt(clean.length === 3 ? clean.split('').map(c => c + c).join('') : clean, 16);
    return window.PDFLib.rgb(
      ((value >> 16) & 255) / 255,
      ((value >> 8) & 255) / 255,
      (value & 255) / 255
    );
  }

  document.addEventListener('click', function (e) {
    const modal = document.getElementById('pdfViewerModal');
    if (modal && e.target === modal) closePdfViewer();
  });
})(window);
