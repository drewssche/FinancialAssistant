(() => {
  window.App.receiptPhotoViewer = function (dialog) {
    const frame = dialog.querySelector('#scanImageFrame');
    const photo = frame.querySelector('canvas');
    const level = dialog.querySelector('#scanZoomLevel');
    const zoomIn = dialog.querySelector('#scanZoomIn');
    const zoomOut = dialog.querySelector('#scanZoomOut');
    const fit = dialog.querySelector('#scanZoomFit');
    const maxScale = 8;
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    let scale = 1, x = 0, y = 0, drag = null;

    function position() {
      const bounds = frame.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      const size = getComputedStyle(photo);
      // Keep the whole photo inside each axis it fits, and cover any axis it overflows.
      const limitX = Math.abs(parseFloat(size.width) * scale - bounds.width) / 2;
      const limitY = Math.abs(parseFloat(size.height) * scale - bounds.height) / 2;
      x = clamp(x, -limitX, limitX);
      y = clamp(y, -limitY, limitY);
      photo.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    }

    // x and y are offsets from the fitted photo's centre in viewport pixels.
    function zoom(next, anchorX = 0, anchorY = 0) {
      const bounded = clamp(next, 1, maxScale);
      const ratio = bounded / scale;
      x = anchorX + (x - anchorX) * ratio;
      y = anchorY + (y - anchorY) * ratio;
      scale = bounded;
      if (scale === 1) {
        x = y = 0;
        photo.style.transform = '';
      } else {
        position();
      }
      level.textContent = Math.round(scale * 100) + '%';
      zoomIn.disabled = scale === maxScale;
      zoomOut.disabled = fit.disabled = scale === 1;
      photo.classList.toggle('is-zoomed', scale > 1);
      photo.tabIndex = scale > 1 ? 0 : -1;
    }

    function endDrag() {
      if (drag && photo.hasPointerCapture(drag.id)) photo.releasePointerCapture(drag.id);
      drag = null;
      photo.classList.remove('is-dragging');
    }

    function reset() {
      endDrag();
      zoom(1);
    }

    function zoomAt(next, event) {
      const bounds = frame.getBoundingClientRect();
      zoom(next, event.clientX - bounds.left - bounds.width / 2, event.clientY - bounds.top - bounds.height / 2);
    }
    photo.addEventListener('click', event => {
      if (dialog.dataset.stage === 'review' && scale === 1) zoomAt(2, event);
    });
    photo.addEventListener('wheel', event => {
      if (dialog.dataset.stage !== 'review' || !event.deltaY) return;
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? frame.clientHeight : 1;
      const next = clamp(scale * Math.exp(-event.deltaY * unit * 0.002), 1, maxScale);
      if (next === 1 && scale === 1) return;
      event.preventDefault();
      if (next !== scale) zoomAt(next, event);
    }, {passive: false});

    photo.addEventListener('pointerdown', event => {
      if (scale === 1 || event.button !== 0 || !event.isPrimary) return;
      event.preventDefault();
      photo.setPointerCapture(event.pointerId);
      drag = {id: event.pointerId, x: event.clientX, y: event.clientY};
      photo.classList.add('is-dragging');
    });
    photo.addEventListener('pointermove', event => {
      if (event.pointerId !== drag?.id) return;
      x += event.clientX - drag.x;
      y += event.clientY - drag.y;
      drag.x = event.clientX;
      drag.y = event.clientY;
      position();
    });
    for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
      photo.addEventListener(type, event => { if (event.pointerId === drag?.id) endDrag(); });
    }

    photo.addEventListener('keydown', event => {
      const arrows = {ArrowLeft: [48, 0], ArrowRight: [-48, 0], ArrowUp: [0, 48], ArrowDown: [0, -48]};
      if (scale === 1 || !arrows[event.key]) return;
      event.preventDefault();
      const [dx, dy] = arrows[event.key];
      x += dx;
      y += dy;
      position();
    });
    zoomIn.onclick = () => zoom(scale * 1.5);
    zoomOut.onclick = () => zoom(scale / 1.5);
    fit.onclick = reset;
    const viewer = dialog.querySelector('#scanPhotoDialog');
    const openPhoto = dialog.querySelector('#scanShowPhoto');
    const column = frame.closest('.scan-image-column'), workspace = column.parentNode;
    const mobile = window.matchMedia('(max-width: 700px)');
    let reviewScroll = 0;
    openPhoto.onclick = () => {
      if (!mobile.matches || photo.hidden || viewer.open) return;
      reviewScroll = dialog.scrollTop;
      viewer.append(column);
      viewer.showModal();
      viewer.querySelector('#scanPhotoClose').focus({preventScroll: true});
    };
    viewer.querySelector('#scanPhotoClose').onclick = () => viewer.close();
    viewer.addEventListener('close', () => {
      if (viewer.open) return;
      workspace.prepend(column);
      if (dialog.open) {
        if (mobile.matches) openPhoto.focus({preventScroll: true});
        dialog.scrollTop = reviewScroll;
      }
    });
    const close = () => { if (viewer.open) viewer.close(); };
    mobile.addEventListener('change', () => { if (!mobile.matches) close(); });
    new ResizeObserver(() => { if (scale > 1) position(); }).observe(frame);
    reset();
    return {reset, close};
  };
})();
