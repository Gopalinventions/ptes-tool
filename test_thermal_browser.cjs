// node test_thermal_browser.cjs <playwright-module-path> <python-exe>
const {chromium}=require(process.argv[2]);
const {spawnSync}=require('child_process');
const assert=require('assert');
(async()=>{
 const source=spawnSync(process.argv[3],['-X','utf8','-c',
  "from thermal_model import *; from designer_integration import design_geometry; from thermal_report import thermal_html; g=design_geometry(125000,15,1.5,2.5,1.16)[1]; r=simulate(g,Settings(),[(3300,0)]*720+[(0,0)]*168+[(0,3300)]*720); print(thermal_html(r,'Demonstration only: 30 days charge, 7 idle, 30 discharge'))"],{cwd:__dirname,encoding:'utf8',maxBuffer:32*1024*1024});
 assert.equal(source.status,0,source.stderr);
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:950}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.setContent(source.stdout);
  assert.equal(await page.locator('#top').innerText(),'40.0 °C');
  await page.locator('#time').fill('720');
  assert.equal(await page.locator('#hour').innerText(),'Hour 720');
  assert.notEqual(await page.locator('#top').innerText(),'40.0 °C');
  await page.screenshot({path:__dirname+'/designer_assets/thermal-preview.png',fullPage:true});
  const before=await page.locator('#hour').innerText();
  await page.locator('#play').click();
  await page.waitForFunction(old=>document.getElementById('hour').textContent!==old,before);
  await page.locator('#play').click();
  assert.equal(await page.locator('#play').innerText(),'Play');
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(errors,[]);
  console.log('PASS thermal animation: initial state, hour selection, temperature update, play/pause, mobile layout, no JS errors');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
