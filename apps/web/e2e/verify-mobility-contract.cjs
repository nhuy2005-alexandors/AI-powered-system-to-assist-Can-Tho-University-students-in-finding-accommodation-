// Compile the same JSON payloads Python validates against real TypeScript types.
// Use a virtual source file; never rewrite the fixture or production code.
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const fixture = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const models = ["CatalogListing", "CatalogPage", "Campus", "RouteRequest", "RouteResult",
  "NearbyRequest", "NearbyResult", "LocationWarning", "Place"];
const virtualPath = path.join(__dirname, "mobility-wire.generated.ts");
const source = `import type { ${models.join(",")} } from "../src/lib/mobility-contracts";\n` +
  models.map((name) => `const ${name.toLowerCase()} = ${JSON.stringify(fixture[name])} satisfies ${name};`).join("\n");
const options = { strict: true, noEmit: true, skipLibCheck: true, target: ts.ScriptTarget.ES2017,
  module: ts.ModuleKind.CommonJS, moduleResolution: ts.ModuleResolutionKind.Node10 };
const host = ts.createCompilerHost(options);
const originalRead = host.readFile.bind(host);
const originalExists = host.fileExists.bind(host);
host.readFile = (name) => path.resolve(name) === path.resolve(virtualPath) ? source : originalRead(name);
host.fileExists = (name) => path.resolve(name) === path.resolve(virtualPath) || originalExists(name);
const program = ts.createProgram([virtualPath], options, host);
const errors = ts.getPreEmitDiagnostics(program).filter((d) => d.category === ts.DiagnosticCategory.Error);
if (errors.length) {
  console.error(ts.formatDiagnostics(errors, {
    getCanonicalFileName: (x) => x, getCurrentDirectory: () => process.cwd(), getNewLine: () => "\n",
  }));
  process.exitCode = 1;
} else {
  console.log("9 shared mobility payloads satisfy TypeScript contracts");
}
