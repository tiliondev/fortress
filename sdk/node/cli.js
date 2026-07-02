#!/usr/bin/env node
// CLI: `tilion-fortress` — launch Fortress and print the CDP URL.
import { Fortress, VERSION } from "./index.js";

const args = process.argv.slice(2);
if (args.includes("--version")) { console.log(`tilion-fortress ${VERSION}`); process.exit(0); }

const portArg = args.indexOf("--port");
const port = portArg >= 0 ? Number(args[portArg + 1]) : 9222;
const headless = !args.includes("--no-headless");

const f = await Fortress.launch({ port, headless });
process.stderr.write(`Fortress up. CDP: ${f.cdpUrl}\n`);
console.log(f.cdpUrl);
process.on("SIGINT", async () => { await f.close(); process.exit(0); });
setInterval(() => {}, 1 << 30);
