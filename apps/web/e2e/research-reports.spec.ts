import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('complete saved validation and adverse-outcome reports download from their research views',async({page,request})=>{
  const run=await(await request.get('/api/runs/current')).json();
  const saved=async(file:string)=>{
    const response=await request.get(`/api/runs/${run.run_id}/reports/${file}`);
    expect(response.status()).toBe(200);return response.text();
  };
  const download=async(label:string)=>{
    const pending=page.waitForEvent('download');await page.getByRole('link',{name:label,exact:true}).click();
    const chunks:Buffer[]=[];for await(const part of (await(await pending).createReadStream())!) chunks.push(Buffer.from(part));
    return Buffer.concat(chunks).toString();
  };
  await page.goto('/');await page.getByRole('button',{name:'Validation Lab',exact:true}).click();
  const validation=await download('Download complete validation report');
  expect(validation).toBe(await saved('model_validation.md'));
  for(const expected of ['archived-validation-atlas-v1',run.run_id,run.sources[0].sha256,run.backtest.period_start,run.backtest.period_end,'Chronology and holdout status','Saved daily-close portfolio risk','Fixed-budget 5x/10x classification','Robustness and negative controls','Zero verified real investment theses']) expect(validation).toContain(expected);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.getByRole('button',{name:'100-Bagger Museum',exact:true}).click();
  const atlas=await download('Download failed-lookalike atlas');
  expect(atlas).toBe(await saved('failed_lookalikes.md'));
  for(const expected of ['archived-validation-atlas-v1',run.run_id,run.sources[0].sha256,'recorded nonpositive terminal outcomes','Recorded case/control assignments','No causal explanation','Missing outcomes stay in coverage counts']) expect(atlas.replace(/\r?\n/g,' ')).toContain(expected);
  await page.setViewportSize({width:390,height:844});
  const link=page.getByRole('link',{name:'Download failed-lookalike atlas',exact:true});await link.focus();await expect(link).toBeFocused();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});
