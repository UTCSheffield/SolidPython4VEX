// Paste into the DevTools console (F12) on any https://www.vexrobotics.com page, in your normal browser.
// It asks for vex_scrape/catalog.json, then downloads every step_url as <name>.<ext> into your Downloads folder.
// Allow "multiple downloads" if the browser asks. Failures are listed at the end; re-run to retry.
(async () => {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".json";
  const file = await new Promise((resolve) => {
    input.onchange = () => resolve(input.files[0]);
    input.click();
  });
  const catalog = JSON.parse(await file.text());
  const failed = [];
  for (const [i, p] of catalog.entries()) {
    try {
      const resp = await fetch(p.step_url, { credentials: "include" });
      if (!resp.ok) throw new Error(resp.status);
      const disp = resp.headers.get("content-disposition") || "";
      const m = disp.match(/filename\*?=(?:UTF-8'')?"?([^";]+)/i);
      const ext = m && m[1].includes(".") ? m[1].slice(m[1].lastIndexOf(".")) : ".zip";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(await resp.blob());
      a.download = p.name + ext;
      a.click();
      console.log(`[${i + 1}/${catalog.length}] ${p.name}${ext}`);
    } catch (e) {
      console.warn(`FAILED ${p.name}: ${e.message}`);
      failed.push(p.name);
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  console.log("Done. Failed:", failed);
})();
