import fs from 'node:fs/promises';
import { chromium } from 'playwright-core';

export const deviceScaleFactor = 3;
export async function openBrowser() {
  return chromium.launch({
    executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  });
}

export async function paint(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
}

export async function measureText(page, groups) {
  return page.evaluate(groups => {
    const context = document.createElement('canvas').getContext('2d');
    const result = [];
    for (const [role, selector] of Object.entries(groups)) {
      for (const node of document.querySelectorAll(selector)) {
        const rect = node.getBoundingClientRect();
        if (!rect.width || !rect.height) continue;
        const style = getComputedStyle(node);
        context.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
        const lines = new Map();
        const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
        let textNode;
        if (node.tagName === 'SELECT') lines.set(rect.top, [node.selectedOptions[0]?.textContent.trim()]);
        else while ((textNode = walker.nextNode())) {
          const range = document.createRange();
          for (const token of textNode.textContent.matchAll(/\S+/g)) {
            range.setStart(textNode, token.index);
            range.setEnd(textNode, token.index + token[0].length);
            const [box] = range.getClientRects();
            if (!box || !box.width) continue;
            // Inline superscripts and small baseline differences belong on the same line.
            const top = [...lines.keys()].find(y => Math.abs(y - box.top) < 4) ?? box.top;
            if (!lines.has(top)) lines.set(top, []);
            lines.get(top).push(token[0]);
          }
        }
        for (const line of lines.values()) {
          const text = line.join(' ');
          if (!/[\p{L}\p{N}]/u.test(text)) continue;
          const glyph = context.measureText(text);
          result.push({ role, text, font: context.font,
            inkHeightCssPx: glyph.actualBoundingBoxAscent + glyph.actualBoundingBoxDescent });
        }
      }
    }
    return result;
  }, groups);
}

export async function writeJson(path, value) {
  await fs.writeFile(path, JSON.stringify(value, null, 2) + '\n', 'utf8');
}
