export const COLOR_MAP = {
  1: '#e6194b', 2: '#3cb44b', 3: '#ffe119', 4: '#9A6324', 5: '#f58231',
  6: '#911eb4', 7: '#000080', 8: '#ffd700', 9: '#800080', 10: '#bdb76b',
  11: '#00ced1', 12: '#ffe4c4', 13: '#696969', 14: '#ff69b4', 15: '#ffff00'
};

export const CLASS_NAMES = {
  1: 'Marine Debris', 2: 'Dense Sargassum', 3: 'Sparse Floating Algae',
  4: 'Natural Organic Material', 5: 'Ship', 6: 'Oil Spill',
  7: 'Marine Water', 8: 'Sediment-Laden Water', 9: 'Foam',
  10: 'Turbid Water', 11: 'Shallow Water', 12: 'Waves & Wakes',
  13: 'Oil Platform', 14: 'Jellyfish', 15: 'Sea snot'
};

export function useMaskProcessing() {
  function parseRGB(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return { r, g, b };
  }

  function processMaskData(maskImg, imgWidth, imgHeight) {
    const canvas = document.createElement('canvas');
    canvas.width = imgWidth;
    canvas.height = imgHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(maskImg, 0, 0, imgWidth, imgHeight);
    const raw = ctx.getImageData(0, 0, imgWidth, imgHeight).data;

    const maskArray = new Uint8Array(imgWidth * imgHeight);
    const counts = {};

    for (let i = 0; i < raw.length; i += 4) {
      const cls = raw[i];
      maskArray[i / 4] = cls;
      if (cls > 0) counts[cls] = (counts[cls] || 0) + 1;
    }

    return { maskArray, counts };
  }

  function buildClassOverlay(maskArray, targetClass, imgWidth, imgHeight) {
    const canvas = document.createElement('canvas');
    canvas.width = imgWidth;
    canvas.height = imgHeight;
    const ctx = canvas.getContext('2d');
    const imgData = ctx.createImageData(imgWidth, imgHeight);
    const data = imgData.data;
    const color = COLOR_MAP[targetClass] || '#999999';
    const rgb = parseRGB(color);

    for (let i = 0; i < maskArray.length; i++) {
      if (maskArray[i] !== targetClass) continue;
      const idx = i * 4;
      data[idx] = rgb.r;
      data[idx + 1] = rgb.g;
      data[idx + 2] = rgb.b;
      data[idx + 3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);
    return canvas.toDataURL();
  }

  function buildMainOverlay(maskArray, counts, totalPixels, threshold, imgWidth, imgHeight) {
    const canvas = document.createElement('canvas');
    canvas.width = imgWidth;
    canvas.height = imgHeight;
    const ctx = canvas.getContext('2d');
    const imgData = ctx.createImageData(imgWidth, imgHeight);
    const data = imgData.data;

    for (let i = 0; i < maskArray.length; i++) {
      const cls = maskArray[i];
      if (!cls) continue;
      if (((counts[cls] || 0) / totalPixels) * 100 < threshold) continue;
      const idx = i * 4;
      const color = COLOR_MAP[cls] || '#999999';
      const rgb = parseRGB(color);
      data[idx] = rgb.r;
      data[idx + 1] = rgb.g;
      data[idx + 2] = rgb.b;
      data[idx + 3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);
    return canvas.toDataURL();
  }

  function buildBoundaryOverlay(maskArray, targetClass, imgWidth, imgHeight) {
    const canvas = document.createElement('canvas');
    canvas.width = imgWidth;
    canvas.height = imgHeight;
    const ctx = canvas.getContext('2d');
    const imgData = ctx.createImageData(imgWidth, imgHeight);
    const data = imgData.data;
    const w = imgWidth, h = imgHeight;

    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        if (maskArray[i] !== targetClass) continue;
        const isEdge =
          x === 0 || x === w - 1 || y === 0 || y === h - 1 ||
          maskArray[i - 1] !== targetClass ||
          maskArray[i + 1] !== targetClass ||
          (i >= w && maskArray[i - w] !== targetClass) ||
          (i + w < maskArray.length && maskArray[i + w] !== targetClass);
        if (isEdge) {
          const idx = i * 4;
          data[idx] = 255;
          data[idx + 1] = 255;
          data[idx + 2] = 255;
          data[idx + 3] = 255;
        }
      }
    }
    ctx.putImageData(imgData, 0, 0);
    return canvas.toDataURL();
  }

  function getClassColor(classId) {
    return COLOR_MAP[classId] || '#999999';
  }

  function getClassName(classId) {
    return CLASS_NAMES[classId] || `Class ${classId}`;
  }

  return {
    COLOR_MAP, CLASS_NAMES,
    processMaskData, buildClassOverlay, buildMainOverlay,
    buildBoundaryOverlay, getClassColor, getClassName
  };
}
