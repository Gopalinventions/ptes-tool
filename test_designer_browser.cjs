// Usage: node test_designer_browser.cjs <playwright-module-path> <python-exe>
const {chromium}=require(process.argv[2]);
const {spawnSync}=require('child_process');
const assert=require('assert');
(async()=>{
 const source=spawnSync(process.argv[3],['-X','utf8','-c',
  'from designer_integration import *; p,g,_=design_geometry(125000,15,1.5,2.5,1.16); print(designer_html(p,g))'],{cwd:__dirname,encoding:'utf8'});
 assert.equal(source.status,0,source.stderr);
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setContent(source.stdout);
  assert(await page.locator('aside').isHidden());
  assert((await page.locator('#metrics').innerText()).includes('125,000'));
  assert((await page.locator('#cadSheet').innerHTML()).length>1000);
  for(const sheet of ['plan','sections','detail']){
   await page.selectOption('#sheetType',sheet);
   assert((await page.locator('#cadSheet').innerHTML()).length>1000);
  }
  await page.locator('#waterColor').fill('#ff0000');
  assert((await page.locator('#three').innerHTML()).includes('#ff0000'));
  assert.equal(await page.locator('#three polygon').last().evaluate(e=>getComputedStyle(e).fill),'rgb(255, 0, 0)');
  const before=await page.locator('#three').innerHTML();
  await page.locator('#angle').fill('45');
  assert.notEqual(await page.locator('#three').innerHTML(),before);
  await page.locator('#cover').check();
  await page.locator('#coverColor').fill('#0000ff');
  assert((await page.locator('#three').innerHTML()).includes('#0000ff'));
  await page.selectOption('#sheetType','plan');
  await page.screenshot({path:__dirname+'/designer_assets/integration-preview.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(errors,[]);
  console.log('PASS: linked HTML, all CAD sheets, volume, colour, rotation, mobile width and no browser errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
