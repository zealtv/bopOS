"""Read-only code review fixtures; all browser storage is ephemeral."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = next(p for p in Path(__file__).resolve().parents if (p/'tools/simfleet.py').exists())
JS = REPO/'dashboard/static/js'

def fixture(browser, scripts, body, setup=''):
    page = browser.new_page()
    page.set_default_timeout(3000)
    page.route('http://review.test/**', lambda route: route.fulfill(body=body, content_type='text/html'))
    page.goto('http://review.test/')
    if setup:
        page.evaluate(setup)
    for script in scripts:
        page.add_script_tag(content=(JS/script).read_text())
    return page

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    results = {}
    page = fixture(browser, ['module-panels.js'], '''<div id="editor-input-control"><select id="editor-input-source"></select></div><div id="monitor-dock"></div><button data-monitor-popout></button><div id="root"></div>''', '''() => {
      window.installation={devices:{dev:{uid:'dev',online:true,report:{io:{modules:{}}}}},
        io_types:{adc:{inputs:[{channel:'0',unit:'V',range:[0,3.3]}],outputs:[]}},
        editor:{active:true,generation:1,io_modules:[{name:'adc',type:'adc'}],input:{source:'simulated',values:{adc:[0]}}}};
      window.selected='dev'; window.Identity={primary:d=>d.uid}; window.handlers={}; window.sent=[];
      window.ws={socket:{readyState:1},on:(t,cb)=>(handlers[t] ||= []).push(cb),send:(t,d)=>sent.push({t,d})};
      window.fire=(t,d)=>handlers[t]?.forEach(cb=>cb(d));
      window.MonitorDock={expand:()=>{},collapse:()=>{}};
    }''')
    page.evaluate('window.component=ModulePanels.mount(document.querySelector("#root"),()=>{},()=>{});fire("state",installation);fire("editor_io",{generation:1,values:{adc:[1]},outputs:{}})')
    results['reconnect'] = page.evaluate('''() => {
      fire('connection',false);fire('connection',true);
      const slider=document.querySelector('[data-module-slider]'); let error=null;
      try {slider.value=2;slider.oninput();} catch(e) {error=String(e);}
      return {enabledBeforeFreshSample:!slider.disabled,error};
    }''')
    assert results['reconnect']['enabledBeforeFreshSample'] and 'null' in results['reconnect']['error']
    results['late_modules'] = page.evaluate('''() => {
      installation.editor.input.source='dev';fire('state',installation);
      const before=document.querySelectorAll('.module-panel').length;
      installation.devices.dev.report.io.modules.adc={type:'adc',state:'running'};
      fire('device_update',{uid:'dev'});
      return {before,after:document.querySelectorAll('.module-panel').length};
    }''')
    assert results['late_modules'] == {'before':0,'after':0}
    page.close()

    page = fixture(browser, ['target-picker.js'], '<div id="root"></div>', '''() => {
      window.storageListeners=[];const add=window.addEventListener.bind(window);
      window.addEventListener=(t,cb,...rest)=>{if(t==='storage')storageListeners.push(cb);add(t,cb,...rest);};
    }''')
    results['picker_cleanup'] = page.evaluate('''() => {
      for(let n=0;n<20;n++) {const host=document.createElement('div');document.body.append(host);
        TargetPicker.create({host,spec:()=>({sections:[]}),followFocusSeat:false});host.remove();}
      return {retainedWindowListeners:storageListeners.length,missingFocus:TargetPicker.focusedSeat()};
    }''')
    assert results['picker_cleanup']['retainedWindowListeners'] == 20
    page.close()

    page = fixture(browser, ['osc-message.js','paramspec.js','param-generator.js','control-surface.js'], '<div id="root"></div>', '''() => {
      window.listenerCounts={}; const add=EventTarget.prototype.addEventListener;
      EventTarget.prototype.addEventListener=function(t,cb,...rest){
        if(this.matches?.('[data-gen-drawer]') && ['focusin','focusout'].includes(t)) listenerCounts[t]=(listenerCounts[t]||0)+1;
        return add.call(this,t,cb,...rest);
      };
      window.installation={live_controls:{declarations:[{identity:'gain',name:'gain',kind:'float',min:0,max:1,default:0}]} };
    }''')
    results['drawer_rebinding'] = page.evaluate('''() => {
      window.surface=ControlSurface.create({getState:()=>installation,send:()=>{},setInteracting:()=>{}});
      const root=document.querySelector('#root'), decl=installation.live_controls.declarations[0];
      root.innerHTML=ParamGenerator.drawer(decl,ParamGenerator.blank(decl,'fade'),{attributes:'data-gen-drawer="seat:0:gain" data-param-path="gain" data-live-scope="seat" data-live-id="0"'});
      surface.bind(root);
      for(let n=0;n<5;n++) root.querySelector('[data-add-param-segment]').click();
      return {rows:root.querySelectorAll('[data-param-segment]').length,listeners:listenerCounts,
        firstRemoveDisabled:root.querySelector('[data-remove-param-segment]').disabled};
    }''')
    assert results['drawer_rebinding']['listeners']['focusin'] == 6
    assert results['drawer_rebinding']['firstRemoveDisabled']
    results['empty_loop'] = page.evaluate('''() => {
      const root=document.querySelector('#root'), decl=installation.live_controls.declarations[0];
      root.innerHTML=ParamGenerator.drawer(decl,ParamGenerator.blank(decl,'loop'),{attributes:'data-gen-drawer="seat:0:gain" data-param-path="gain" data-live-scope="seat" data-live-id="0"'});
      surface.bind(root);
      root.querySelector('[data-remove-param-segment]').click();
      const lastEnabled=!root.querySelector('[data-remove-param-segment]').disabled;
      root.querySelector('[data-remove-param-segment]').click();
      return {lastRemoveEnabled:lastEnabled,remainingRows:root.querySelectorAll('[data-param-segment]').length};
    }''')
    assert results['empty_loop'] == {'lastRemoveEnabled':True,'remainingRows':0}
    page.close()

    page = fixture(browser, ['spatial.js'], '<svg id="spatial"></svg>', '''() => {
      window.installation={room:{width:10,depth:8},seats:{0:{id:0,positions:[[1,1]],groups:[]}},devices:{},points:{}};
      window.socket={send:()=>{}};document.querySelector('svg').setPointerCapture=()=>{};
    }''')
    results['spatial_cancel'] = page.evaluate('''() => {
      Spatial.render(installation,0,()=>{},socket);
      const svg=document.querySelector('svg');
      svg.querySelector('circle[data-point]').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:1,clientX:10,clientY:10}));
      svg.dispatchEvent(new PointerEvent('pointercancel',{bubbles:true,pointerId:1}));
      installation.seats[1]={id:1,positions:[[2,2]],groups:[]};Spatial.render(installation,0,()=>{},socket);
      return {draggingAfterCancel:Spatial.dragging,renderedSeats:svg.querySelectorAll('[data-seat-id]').length};
    }''')
    assert results['spatial_cancel'] == {'draggingAfterCancel':True,'renderedSeats':1}
    page.close()
    page = fixture(browser, ['target-picker.js','control-surface.js','control-column.js'], '<div id="root"></div>', '''() => {
      window.installation={devices:{},groups:{},seats:{0:{id:0,name:'Seat 0',params:{}}},facilitator_commands:['reboot']};
      window.sent=[];window.GroupSlots={palette:[]};
    }''')
    page.evaluate('''() => {
      window.column=ControlColumn.create({host:document.querySelector('#root'),
        getState:()=>installation,isInteracting:()=>false,sendCommand:p=>sent.push(p),
        capabilities:{targetPicker:false,deriveAllTargets:true,deviceCommands:true}});
      column.render();document.querySelector('[data-command-key]').open=true;
    }''')
    button = page.locator('[data-live-scope="all"][data-target-command="reboot"]')
    box = button.bounding_box()
    page.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2)
    page.mouse.down()
    page.evaluate('column.render()')
    page.mouse.up()
    page.wait_for_timeout(1300)
    results['detached_hold'] = page.evaluate('sent')
    assert results['detached_hold'] == [{'scope':'all','verb':'reboot'}]
    page.close()
    browser.close()
    print(json.dumps(results,indent=2))
