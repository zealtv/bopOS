#!/usr/bin/env python3
"""Cancelled/capture-lost drags release both Spatial maps for fresh state."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "tools/simfleet.py").exists())
FAILURES = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    for ending in ("pointercancel", "lostpointercapture"):
        for kind, selector in (
            ("seat", "#spatial circle[data-point]"),
            ("point", "#spatial g[data-point-id]"),
            ("listener", "#spatial g[data-listener]"),
            ("heading", "#spatial .listener-tip"),
            ("range", "#spatial .listener-collar"),
            ("editor", "#editor-spatial g[data-editor-point-id]"),
        ):
            for moved in (False, True):
                page = browser.new_page()
                page.set_default_timeout(3000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.set_content('''
                    <svg id="spatial" width="600" height="500"></svg>
                    <div id="editor-preview"><svg id="editor-spatial"
                      width="600" height="500"></svg></div>
                    <div id="editor-point-list"></div>
                    <div id="editor-point-controls">
                      <span id="editor-point-title"></span>
                      <input id="editor-point-radius" type="number">
                      <input id="editor-point-falloff" type="number">
                      <button id="editor-point-delete"></button>
                    </div>
                    <button id="editor-point-add"></button>
                ''')
                page.evaluate('''() => {
                    window.installation = {room:{width:10,depth:8},
                      seats:{0:{id:0,positions:[[1,1]],groups:[]}}, devices:{},
                      points:{0:{id:0,x:3,y:3,r:2,falloff:1}},
                      listener:{x:5,y:4,heading:0,range:3},simulation:{active:true}};
                    window.editor = {active:true,points:{0:{id:0,x:0,y:0,r:2,falloff:1}}};
                    window.sent = []; window.selected = [];
                    window.socket = {send:(type,data)=>sent.push({type,data})};
                    window.select = id => selected.push(id);
                    // Synthetic pointers are not active browser pointers.
                    for (const svg of document.querySelectorAll('svg'))
                      svg.setPointerCapture = () => {};
                }''')
                page.add_script_tag(path=str(REPO / "dashboard/static/js/spatial.js"))
                result = page.evaluate('''({ending,selector,moved,kind}) => {
                    Spatial.render(installation,0,select,socket);
                    Spatial.renderEditor(editor,socket);
                    const target = document.querySelector(selector);
                    const svg = target.closest('svg');
                    const pointer = (type,x=100,y=100) => new PointerEvent(type,
                      {bubbles:true,pointerId:1,clientX:x,clientY:y});
                    target.dispatchEvent(pointer('pointerdown'));
                    const started = Spatial.dragging;
                    if (moved) svg.dispatchEvent(pointer('pointermove',250,220));
                    // A newer snapshot is held back by the drag's render guard.
                    installation = structuredClone(installation);
                    installation.seats[1] = {id:1,positions:[[2,2]],groups:[]};
                    editor = structuredClone(editor);
                    editor.points[1] = {id:1,x:1,y:1,r:2,falloff:1};
                    Spatial.render(installation,0,select,socket);
                    Spatial.renderEditor(editor,socket);
                    const before = sent.length;
                    svg.dispatchEvent(pointer(ending));
                    const ended = !Spatial.dragging;
                    const redrawn = kind === 'editor'
                      ? svg.querySelectorAll('[data-editor-point-id]').length === 2
                      : svg.querySelectorAll('[data-seat-id]').length === 2;
                    // Duplicate termination and a late up must be harmless.
                    svg.dispatchEvent(pointer('lostpointercapture'));
                    svg.dispatchEvent(pointer('pointerup'));
                    const noCompletion = sent.length === before && selected.length === 0;
                    const noScrub = !svg.querySelector('.scrubbing');
                    const next = document.querySelector(selector);
                    next.dispatchEvent(pointer('pointerdown'));
                    const restarted = Spatial.dragging;
                    svg.dispatchEvent(pointer('pointermove',300,250));
                    const beforeUp = sent.length;
                    svg.dispatchEvent(pointer('pointerup'));
                    return {started,ended,redrawn,noCompletion,noScrub,restarted,
                      completed:!Spatial.dragging && sent.length > beforeUp};
                }''', dict(ending=ending, selector=selector, moved=moved, kind=kind))
                label = f"{kind} {ending} ({'moved' if moved else 'unmoved'})"
                passed = all(result.values()) and not errors
                print(f"[{'PASS' if passed else 'FAIL'}] {label}: {result}")
                if errors:
                    print(f"  Browser errors: {errors}")
                if not passed:
                    FAILURES.append(label)
                page.close()
    browser.close()

print(f"Spatial cancellation: {24 - len(FAILURES)} passed, {len(FAILURES)} failed")
raise SystemExit(bool(FAILURES))
