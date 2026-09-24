#!/usr/bin/env node
/**
 * render.js — drive a composition deterministically in headless Chromium
 *
 *   node render.js stills <index.html> <out-dir> <t1,t2,…>
 *   node render.js frames <index.html> <out-dir> <from-frame> <to-frame>  (to-frame is exclusive)
 *   node render.js cues   <index.html> <cues.json>
 *   node render.js check  <index.html> [report.json]
 *
 * The page must expose window.renderAt(t) and window.SFX. Viewport size is read from the
 * composition's --W / --H CSS variables so one renderer serves vertical and landscape.
 */
const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(__dirname, 'node_modules', 'playwright-core'));

const FPS = 30;
const [,, mode, htmlFile, target, a, b] = process.argv;

function usage(message) {
  console.error(message);
  console.error('Usage: render.js stills|frames|cues|check <index.html> [out] [args]');
  process.exit(1);
}

if (!['stills', 'frames', 'cues', 'check'].includes(mode)) usage(`Unknown mode: ${mode}`);
if (!htmlFile || !fs.existsSync(htmlFile)) usage(`No such composition: ${htmlFile}`);
if (mode === 'frames' && (Number.isNaN(Number(a)) || Number.isNaN(Number(b)) || b === undefined)) {
  usage(`frames needs <from-frame> <to-frame> as two separate numbers, got: ${a} ${b}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  // Media elements abort in-flight range requests once buffered; only real misses matter
  page.on('requestfailed', request => {
    if (request.failure()?.errorText !== 'net::ERR_ABORTED') errors.push(`missing file ${request.url()}`);
  });
  await page.goto('file://' + path.resolve(htmlFile), { waitUntil: 'load' });
  if (!(await page.evaluate(() => typeof window.renderAt === 'function'))) {
    errors.forEach(message => console.error(`PAGE ERROR ${message}`));
    console.error('Composition did not initialise (window.renderAt is missing).');
    console.error('Next: a missing vendor/ file means setup.sh has not completed — re-run it; otherwise fix the first PAGE ERROR');
    await browser.close();
    process.exit(2);
  }
  const size = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    return { width: parseInt(style.getPropertyValue('--W')), height: parseInt(style.getPropertyValue('--H')) };
  });
  await page.setViewportSize(size);
  await page.evaluate(() => document.fonts.ready);

  if (mode === 'cues') {
    const cues = await page.evaluate(() => window.SFX);
    fs.writeFileSync(target, JSON.stringify(cues));
    console.log(`${cues.length} sound cues → ${target}`);
  }

  // Layout QA without eyes: measure every shot at its midpoint and report what a still would show
  if (mode === 'check') {
    const shots = await page.evaluate(() => window.SHOTS || []);
    if (!shots.length) {
      console.error('No shots registered in window.SHOTS');
      console.error('Next: author the timeline with shot()/faceCam(), or re-fill the template if it predates window.SHOTS');
      await browser.close();
      process.exit(2);
    }

    const report = [];
    for (const shotWindow of shots) {
      const mid = shotWindow.s + (shotWindow.e - shotWindow.s) / 2;
      await page.evaluate(x => window.renderAt(x), mid);
      const found = await page.evaluate(({ id, W, H }) => {
        const section = document.getElementById(id);
        if (!section) return { missing: true, overflow: [], collide: [], visible: 0 };
        const decorative = /gridbg|glow|scan|track|pkt|bars|strike|vhs|hl|tape/;
        const named = el => (el.id ? '#' + el.id : '.' + ((el.getAttribute('class') || el.tagName.toLowerCase()).split(' ')[0]));
        const capbox = document.getElementById('capbox');
        const capRect = capbox && capbox.style.visibility !== 'hidden' && capbox.children.length
          ? capbox.getBoundingClientRect()
          : null;
        const out = { missing: false, overflow: [], collide: [], visible: 0 };
        for (const el of section.querySelectorAll('*')) {
          const classes = el.getAttribute('class') || '';
          if (decorative.test(classes)) continue;
          const style = getComputedStyle(el);
          if (style.visibility === 'hidden' || style.display === 'none' || parseFloat(style.opacity) < 0.05) continue;
          const rect = el.getBoundingClientRect();
          if (rect.width < 2 || rect.height < 2) continue;
          const isText = [...el.children].every(c => c.tagName === 'BR' || decorative.test(c.getAttribute('class') || '')) && el.textContent.trim().length > 0;
          const isBlock = el.tagName === 'IMG' || el.tagName === 'VIDEO' || /card|term|logo|stamp|badge/.test(classes);
          if (!isText && !isBlock) continue;
          out.visible += 1;
          // A centred .cx block spans the whole frame even when its text runs past the edge, so
          // measure the text itself; images and cards are measured by their own box
          let box = rect;
          if (isText) {
            const range = document.createRange();
            range.selectNodeContents(el);
            const textRect = range.getBoundingClientRect();
            if (textRect.width > 1 && textRect.height > 1) box = textRect;
          }
          if (box.left < -2 || box.top < -2 || box.right > W + 2 || box.bottom > H + 2) {
            out.overflow.push(`${named(el)} at ${Math.round(box.left)},${Math.round(box.top)} ${Math.round(box.width)}x${Math.round(box.height)}`);
          }
          if (capRect && isText && box.left < capRect.right && box.right > capRect.left && box.top < capRect.bottom && box.bottom > capRect.top) {
            out.collide.push(named(el));
          }
        }
        return out;
      }, { id: shotWindow.id, W: size.width, H: size.height });
      report.push({ ...shotWindow, at: Number(mid.toFixed(2)), ...found });
    }

    const flagged = report.filter(r => r.missing || !r.visible || r.overflow.length || r.collide.length);
    const total = key => report.reduce((sum, r) => sum + r[key].length, 0);
    if (target) fs.writeFileSync(target, JSON.stringify(report, null, 2));
    console.log(`${report.length} shots checked · ${total('overflow')} past the frame edge · ${total('collide')} caption collisions · ${report.filter(r => !r.missing && !r.visible).length} empty`);
    for (const r of flagged) {
      if (r.missing) console.log(`  ${r.id} missing — no element with that id`);
      else if (!r.visible) console.log(`  ${r.id} empty at ${r.at}s — nothing visible`);
      r.overflow.forEach(item => console.log(`  ${r.id} past the edge: ${item}`));
      r.collide.forEach(item => console.log(`  ${r.id} under the captions: ${item}`));
    }
    errors.forEach(message => console.error(`PAGE ERROR ${message}`));
    await browser.close();
    if (flagged.length || errors.length) {
      console.log('Next: fix those shots (resize the type, move it inside the safe zone, or hide captions with NOCAP), then re-run check');
      process.exit(1);
    }
    console.log('Next: render stills if you can view images, then render frames');
    process.exit(0);
  }

  if (mode === 'stills') {
    fs.mkdirSync(target, { recursive: true });
    if (!a) {
      usage('stills needs a comma-separated timestamp list');
    }
    const times = a.split(',').map(s => Number(s.trim())).filter(t => !Number.isNaN(t));
    if (!times.length) {
      usage('stills timestamp list parsed to zero valid numbers');
    }
    for (const t of times) {
      await page.evaluate(x => window.renderAt(x), t);
      await page.screenshot({ path: path.join(target, `t${String(t.toFixed(2)).padStart(7, '0')}.jpg`), type: 'jpeg', quality: 70 });
    }
    console.log(`${times.length} stills → ${target}`);
  }

  if (mode === 'frames') {
    fs.mkdirSync(target, { recursive: true });
    for (let f = Number(a); f < Number(b); f++) {
      await page.evaluate(x => window.renderAt(x), f / FPS);
      await page.screenshot({ path: path.join(target, `f${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 92 });
    }
  }

  await browser.close();
  if (errors.length) {
    errors.forEach(message => console.error(`PAGE ERROR ${message}`));
    process.exit(2);
  }
})().catch(e => { console.error(e.message); process.exit(1); });
